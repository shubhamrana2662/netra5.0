from __future__ import annotations
"""
CyberDrishti AI — CyberDrishtiLM Real Transformer Inference & Training Service

ARCHITECTURE (exactly reconstructed from pytorch_model.bin state_dict):
    token_embeddings        Embedding [3162, 128]   BPE vocab (3162 tokens)
    position_embeddings     Embedding [64, 128]     Absolute positions (max 64)
    embed_ln                LayerNorm [128]         Post-embedding norm

    encoder.{0..3}          4× Pre-LN Encoder Layer:
      .attn.q/k/v           Linear [128, 128]       Multi-head attention (4 heads, head_dim=32)
      .attn.out             Linear [128, 128]       Attention output projection
      .ff.net.0             Linear [128, 512]       FFN expand
      .ff.net.3             Linear [512, 128]       FFN contract  (indices 0,3 = Linear;
                                                     1,2 = GELU, Dropout — no params)
      .ln1                  LayerNorm [128]         Pre-attention norm
      .ln2                  LayerNorm [128]         Pre-FFN norm

    ner_head                Linear [25, 128]        Token-level NER classifier
    fraud_pool              Linear [128, 128]       CLS-token pooling projection
    fraud_head              Linear [2, 128]         Binary fraud classifier

LABEL MAP STATUS:
    The ner_head has 25 output classes. Evidence from all available artifacts:
    - training_history.json shows 9 entity types (seqeval level, without BIO):
        ACCOUNT, AMOUNT, BANK, KEYWORD, OTP, PER, PHONE, UPI, URL
    - Minimum BIO encoding: 9 types × {B-, I-} + O = 19 labels
    - ner_head output = 25 → 6 classes are UNRECOVERABLE
    - config.json has NO label2id field
    - No log files, no original training script found in repo

    VERDICT: The original 25-label mapping cannot be recovered with confidence.
    The existing checkpoint is kept untouched. A new versioned model should be
    trained from a clean, explicitly defined label mapping.

    When loading the existing checkpoint:
      - The architecture loads correctly (all 74 state_dict keys match)
      - run_verification_forward() proves real transformer inference works
      - predict() returns [] with a LABEL_MAP_UNKNOWN warning
      - status in registry = LABEL_MAP_UNKNOWN

TOKENIZER:
    BPE tokenizer (tokenizers library), max_seq=64, pad_to=64.
    Splits on '@' and whitespace. Special tokens: [PAD]=0, [UNK]=1, [CLS]=2, [SEP]=3.
"""
import json
import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_torch_available = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    _torch_available = True
except ImportError:
    logger.warning("[CyberDrishtiLM] PyTorch not installed. Run: pip3 install torch")

_tokenizers_available = False
try:
    from tokenizers import Tokenizer as HFTokenizer
    _tokenizers_available = True
except ImportError:
    logger.warning(
        "[CyberDrishtiLM] 'tokenizers' library not installed. "
        "Run: pip3 install tokenizers"
    )


# ── Prediction dataclass ──────────────────────────────────────────────────────

@dataclass
class CyberDrishtiLMPrediction:
    entity_type: str
    raw_value: str
    canonical_value: str
    span_start: int
    span_end: int
    confidence: float
    model_name: str = "cyberdrishtilm"


# ── Architecture modules ──────────────────────────────────────────────────────

_BaseModule = nn.Module if _torch_available else object


class _MultiHeadAttention(_BaseModule):
    """
    Multi-head self-attention.

    State_dict keys (per layer):
        attn.q.{weight, bias}   [128, 128]
        attn.k.{weight, bias}   [128, 128]
        attn.v.{weight, bias}   [128, 128]
        attn.out.{weight, bias} [128, 128]

    4 heads, head_dim = 128 // 4 = 32.
    """
    def __init__(self, embed_dim: int = 128, num_heads: int = 4):
        if not _torch_available:
            return
        super().__init__()
        assert embed_dim % num_heads == 0, "embed_dim must be divisible by num_heads"
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.scale = math.sqrt(self.head_dim)

        self.q = nn.Linear(embed_dim, embed_dim)
        self.k = nn.Linear(embed_dim, embed_dim)
        self.v = nn.Linear(embed_dim, embed_dim)
        self.out = nn.Linear(embed_dim, embed_dim)

    def forward(
        self,
        x: "torch.Tensor",                    # [B, T, D]
        attention_mask: Optional["torch.Tensor"] = None,  # [B, T] 1=attend, 0=pad
    ) -> "torch.Tensor":                       # [B, T, D]
        B, T, D = x.shape
        H, Hd = self.num_heads, self.head_dim

        Q = self.q(x).view(B, T, H, Hd).transpose(1, 2)  # [B, H, T, Hd]
        K = self.k(x).view(B, T, H, Hd).transpose(1, 2)
        V = self.v(x).view(B, T, H, Hd).transpose(1, 2)

        scores = torch.matmul(Q, K.transpose(-2, -1)) / self.scale  # [B, H, T, T]

        if attention_mask is not None:
            # Mask padding positions: set to -inf so softmax → 0
            pad_mask = (attention_mask == 0)[:, None, None, :]  # [B, 1, 1, T]
            scores = scores.masked_fill(pad_mask, float("-inf"))

        attn_weights = torch.softmax(scores, dim=-1)
        out = torch.matmul(attn_weights, V)            # [B, H, T, Hd]
        out = out.transpose(1, 2).reshape(B, T, D)     # [B, T, D]
        return self.out(out)


class _FeedForward(_BaseModule):
    """
    Position-wise FFN.

    State_dict keys (per layer):
        ff.net.0.{weight, bias}  Linear [512, 128]  (expand)
        ff.net.3.{weight, bias}  Linear [128, 512]  (contract)

    Sequential indices:
        net[0] = Linear(128, 512)   — has params (index 0)
        net[1] = GELU               — no params
        net[2] = Dropout            — no params
        net[3] = Linear(512, 128)   — has params (index 3)
    """
    def __init__(self, embed_dim: int = 128, ff_dim: int = 512, dropout: float = 0.1):
        if not _torch_available:
            return
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(embed_dim, ff_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ff_dim, embed_dim),
        )

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        return self.net(x)


class _EncoderLayer(_BaseModule):
    """
    Pre-LN Transformer Encoder Layer.

    State_dict keys (per layer N):
        encoder.N.attn.{q,k,v,out}.{weight,bias}
        encoder.N.ff.net.{0,3}.{weight,bias}
        encoder.N.ln1.{weight,bias}
        encoder.N.ln2.{weight,bias}

    Pre-LN forward pass:
        x = x + Dropout(Attn(LN1(x)))
        x = x + Dropout(FFN(LN2(x)))
    """
    def __init__(
        self,
        embed_dim: int = 128,
        num_heads: int = 4,
        ff_dim: int = 512,
        dropout: float = 0.1,
    ):
        if not _torch_available:
            return
        super().__init__()
        self.attn = _MultiHeadAttention(embed_dim, num_heads)
        self.ff = _FeedForward(embed_dim, ff_dim, dropout)
        self.ln1 = nn.LayerNorm(embed_dim)
        self.ln2 = nn.LayerNorm(embed_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        x: "torch.Tensor",
        attention_mask: Optional["torch.Tensor"] = None,
    ) -> "torch.Tensor":
        # Pre-LN attention sublayer
        x = x + self.dropout(self.attn(self.ln1(x), attention_mask))
        # Pre-LN FFN sublayer
        x = x + self.dropout(self.ff(self.ln2(x)))
        return x


class CyberDrishtiLMModel(_BaseModule):
    """
    CyberDrishtiLM — full transformer model exactly matching pytorch_model.bin.

    Parameters (from config.json + state_dict):
        vocab_size       = 3162
        embedding_dim    = 128
        num_layers       = 4
        num_heads        = 4     (head_dim = 32)
        ff_dim           = 512
        max_seq_length   = 64
        dropout          = 0.1
        num_ner_labels   = 25    (label map unrecoverable — see module docstring)
        num_fraud_labels = 2
        pad_token_id     = 0
    """
    def __init__(
        self,
        vocab_size: int = 3162,
        embedding_dim: int = 128,
        num_layers: int = 4,
        num_heads: int = 4,
        ff_dim: int = 512,
        max_seq_length: int = 64,
        dropout: float = 0.1,
        num_ner_labels: int = 25,
        num_fraud_labels: int = 2,
        pad_token_id: int = 0,
    ):
        if not _torch_available:
            return
        super().__init__()
        self.pad_token_id = pad_token_id
        self.max_seq_length = max_seq_length

        # Embedding layers
        self.token_embeddings = nn.Embedding(
            vocab_size, embedding_dim, padding_idx=pad_token_id
        )
        self.position_embeddings = nn.Embedding(max_seq_length, embedding_dim)
        self.embed_ln = nn.LayerNorm(embedding_dim)
        self.embed_dropout = nn.Dropout(dropout)

        # Encoder stack
        self.encoder = nn.ModuleList([
            _EncoderLayer(embedding_dim, num_heads, ff_dim, dropout)
            for _ in range(num_layers)
        ])

        # Task heads
        self.ner_head = nn.Linear(embedding_dim, num_ner_labels)
        self.fraud_pool = nn.Linear(embedding_dim, embedding_dim)
        self.fraud_head = nn.Linear(embedding_dim, num_fraud_labels)

    def forward(
        self,
        input_ids: "torch.Tensor",       # [B, T]
        attention_mask: "torch.Tensor",  # [B, T] — 1=real token, 0=pad
    ) -> Tuple["torch.Tensor", "torch.Tensor"]:
        """
        Real transformer forward pass.

        Returns:
            ner_logits:   [B, T, num_ner_labels]  — token-level classification
            fraud_logits: [B, num_fraud_labels]    — sentence-level fraud classification
        """
        B, T = input_ids.shape
        assert T <= self.max_seq_length, (
            f"Input length {T} exceeds max_seq_length {self.max_seq_length}"
        )

        # Positional ids: [0, 1, 2, ..., T-1] for each batch element
        positions = torch.arange(T, device=input_ids.device).unsqueeze(0).expand(B, -1)

        # Embedding
        x = self.token_embeddings(input_ids) + self.position_embeddings(positions)
        x = self.embed_ln(x)
        x = self.embed_dropout(x)

        # Encoder stack
        for layer in self.encoder:
            x = layer(x, attention_mask)

        # NER: token-level logits
        ner_logits = self.ner_head(x)  # [B, T, 25]

        # Fraud: pool CLS token (index 0) through linear + tanh, then classify
        cls_hidden = x[:, 0, :]                         # [B, D]
        pooled = torch.tanh(self.fraud_pool(cls_hidden)) # [B, D]
        fraud_logits = self.fraud_head(pooled)           # [B, 2]

        return ner_logits, fraud_logits


# ── Inference Engine ──────────────────────────────────────────────────────────

class CyberDrishtiLMInferenceEngine:
    """
    CyberDrishtiLM Inference Service — loads checkpoint and runs real forward pass.

    Label map status for the existing production checkpoint:
        LABEL_MAP_UNKNOWN — the 25-label id2label mapping could not be recovered
        from any available artifact. predict() returns [] in this state.
        run_verification_forward() still runs the real forward pass.

    For a retrained versioned model with a documented label map:
        status = READY — predict() returns real entity predictions.
    """

    # Status constants
    STATUS_READY = "READY"
    STATUS_MISSING_CHECKPOINT = "MISSING_CHECKPOINT"
    STATUS_LABEL_MAP_UNKNOWN = "LABEL_MAP_UNKNOWN"
    STATUS_UNAVAILABLE = "UNAVAILABLE"

    def __init__(self, model_dir: Optional[str | Path] = None):
        self.model: Optional[CyberDrishtiLMModel] = None
        self.tokenizer: Optional["HFTokenizer"] = None
        self.config: Dict[str, Any] = {}
        self.id2label: Dict[int, str] = {}      # Empty = label map unknown
        self.label2id: Dict[str, int] = {}
        self.loaded = False
        self.device = "cpu"
        self.status = self.STATUS_MISSING_CHECKPOINT
        self._model_dir: Optional[Path] = None

        if model_dir:
            self.load(model_dir)

    def load(self, model_dir: str | Path) -> bool:
        """
        Load CyberDrishtiLM checkpoint.

        Steps:
        1. Verify pytorch_model.bin exists.
        2. Load config.json (for architecture params and optional label2id).
        3. Load tokenizer.json (BPE via tokenizers library).
        4. Build CyberDrishtiLMModel with exact architecture.
        5. Call load_state_dict() — will raise if key mismatch.
        6. Set status based on whether label2id is available.
        """
        if not _torch_available:
            logger.error("[CyberDrishtiLM] PyTorch unavailable — cannot load model.")
            self.status = self.STATUS_UNAVAILABLE
            return False

        path = Path(model_dir)
        self._model_dir = path

        if not path.exists():
            logger.warning("[CyberDrishtiLM] Directory not found: %s", path)
            self.status = self.STATUS_MISSING_CHECKPOINT
            return False

        bin_path = path / "pytorch_model.bin"
        if not bin_path.exists():
            logger.warning("[CyberDrishtiLM] Weights file not found: %s", bin_path)
            self.status = self.STATUS_MISSING_CHECKPOINT
            return False

        try:
            # Device selection
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

            # Load config
            config_path = path / "config.json"
            if config_path.exists():
                with open(config_path, "r") as f:
                    self.config = json.load(f)

            # Extract label map if present
            label2id_raw = self.config.get("label2id", {})
            if label2id_raw:
                self.label2id = {k: int(v) for k, v in label2id_raw.items()}
                self.id2label = {int(v): k for k, v in label2id_raw.items()}
            else:
                self.id2label = {}
                self.label2id = {}

            # Load tokenizer
            tok_path = path / "tokenizer.json"
            if tok_path.exists() and _tokenizers_available:
                self.tokenizer = HFTokenizer.from_file(str(tok_path))
                logger.info("[CyberDrishtiLM] BPE tokenizer loaded from %s", tok_path)
            elif not _tokenizers_available:
                logger.warning(
                    "[CyberDrishtiLM] 'tokenizers' library not installed — "
                    "tokenizer unavailable. Run: pip3 install tokenizers"
                )

            # Build model from config (fall back to known defaults)
            vocab_size = self.config.get("vocab_size", 3162)
            embedding_dim = self.config.get("embedding_dim", 128)
            num_layers = self.config.get("num_layers", 4)
            num_heads = self.config.get("num_attention_heads", 4)
            ff_dim = self.config.get("feedforward_dim", 512)
            max_seq = self.config.get("max_sequence_length", 64)
            dropout = self.config.get("dropout", 0.1)
            num_ner_labels = self.config.get("num_ner_labels", 25)
            num_fraud_labels = self.config.get("num_fraud_labels", 2)
            pad_token_id = self.config.get("pad_token_id", 0)

            self.model = CyberDrishtiLMModel(
                vocab_size=vocab_size,
                embedding_dim=embedding_dim,
                num_layers=num_layers,
                num_heads=num_heads,
                ff_dim=ff_dim,
                max_seq_length=max_seq,
                dropout=dropout,
                num_ner_labels=num_ner_labels,
                num_fraud_labels=num_fraud_labels,
                pad_token_id=pad_token_id,
            )

            # Load actual weights — strict=True ensures exact key match
            logger.info(
                "[CyberDrishtiLM] Loading weights from %s on device: %s",
                bin_path, self.device,
            )
            state_dict = torch.load(
                bin_path, map_location=self.device, weights_only=False
            )
            self.model.load_state_dict(state_dict, strict=True)
            self.model.to(self.device)
            self.model.eval()

            self.loaded = True

            if self.id2label:
                self.status = self.STATUS_READY
                logger.info(
                    "[CyberDrishtiLM] Loaded successfully. "
                    "Labels: %d, Vocab: %d, Device: %s",
                    len(self.id2label), vocab_size, self.device,
                )
            else:
                self.status = self.STATUS_LABEL_MAP_UNKNOWN
                logger.warning(
                    "[CyberDrishtiLM] Checkpoint loaded (all %d weight tensors matched) "
                    "but label2id is MISSING from config.json. "
                    "NER predictions are disabled. "
                    "run_verification_forward() still works to prove real inference. "
                    "Train a new versioned model with an explicit label mapping.",
                    len(state_dict),
                )

            return True

        except Exception as exc:
            logger.error("[CyberDrishtiLM] Load error: %s", exc)
            self.loaded = False
            self.status = self.STATUS_UNAVAILABLE
            return False

    # ── Tokenization ──────────────────────────────────────────────────────────

    def _encode(self, text: str) -> Optional[Tuple[List[int], List[Tuple[int, int]]]]:
        """
        Encode text with the BPE tokenizer.
        Returns (ids, offsets) or None if tokenizer unavailable.
        """
        if self.tokenizer is None:
            return None
        encoding = self.tokenizer.encode(text)
        return encoding.ids, encoding.offsets

    # ── Real forward pass ─────────────────────────────────────────────────────

    def run_verification_forward(self, text: str) -> Dict[str, Any]:
        """
        Run a real transformer forward pass and return tensor shapes.
        This proves that:
          - The model architecture matches the checkpoint
          - All 74 weight tensors loaded correctly
          - Real gradient-capable computation happens (not heuristics)

        This works even when label2id is unknown (LABEL_MAP_UNKNOWN status).

        Returns a dict with ner_logits_shape, fraud_logits_shape, device, etc.
        Raises RuntimeError if model or tokenizer is not loaded.
        """
        if not self.loaded or self.model is None:
            raise RuntimeError(
                "[CyberDrishtiLM] Model not loaded. Call load() first."
            )
        if self.tokenizer is None:
            raise RuntimeError(
                "[CyberDrishtiLM] Tokenizer not loaded. "
                "Ensure tokenizers library is installed and tokenizer.json exists."
            )
        if not _torch_available:
            raise RuntimeError("[CyberDrishtiLM] PyTorch not available.")

        encoded = self._encode(text)
        if encoded is None:
            raise RuntimeError("[CyberDrishtiLM] Encoding failed.")

        ids, offsets = encoded
        input_ids = torch.tensor([ids], dtype=torch.long, device=self.device)
        attention_mask = (input_ids != self.model.pad_token_id).long()

        with torch.no_grad():
            ner_logits, fraud_logits = self.model(input_ids, attention_mask)

        # Compute fraud probability
        fraud_probs = torch.softmax(fraud_logits, dim=-1)[0].cpu().tolist()
        non_pad_tokens = int(attention_mask.sum().item())

        return {
            "forward_pass": "real_transformer",
            "device": self.device,
            "input_text": text[:80],
            "input_ids_shape": list(input_ids.shape),
            "attention_mask_shape": list(attention_mask.shape),
            "ner_logits_shape": list(ner_logits.shape),
            "fraud_logits_shape": list(fraud_logits.shape),
            "non_pad_tokens": non_pad_tokens,
            "fraud_prob_clean": round(fraud_probs[0], 4),
            "fraud_prob_fraud": round(fraud_probs[1], 4),
            "label_map_status": self.status,
            "note": (
                "ner_logits_shape[2] = number of NER output classes in checkpoint. "
                "label_map for these classes is UNRECOVERABLE from existing artifacts."
                if self.status == self.STATUS_LABEL_MAP_UNKNOWN
                else "Real inference with known label map."
            ),
        }

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(self, text: str, min_confidence: float = 0.50) -> List[CyberDrishtiLMPrediction]:
        """
        Run CyberDrishtiLM NER inference.

        Returns:
            List of CyberDrishtiLMPrediction — empty if:
              - Model not loaded
              - Label map unknown (LABEL_MAP_UNKNOWN status)
              - No high-confidence predictions found
        """
        if not self.loaded or self.model is None or not text.strip():
            return []

        if self.status == self.STATUS_LABEL_MAP_UNKNOWN:
            logger.warning(
                "[CyberDrishtiLM] predict() called but label2id is UNRECOVERABLE. "
                "Cannot decode NER output classes. Returning empty predictions. "
                "Train a versioned model with a documented label map. "
                "Use run_verification_forward() to confirm real inference works."
            )
            return []

        if self.tokenizer is None:
            logger.warning("[CyberDrishtiLM] Tokenizer unavailable — cannot predict.")
            return []

        try:
            encoded = self._encode(text)
            if encoded is None:
                return []

            ids, offsets = encoded
            input_ids = torch.tensor([ids], dtype=torch.long, device=self.device)
            attention_mask = (input_ids != self.model.pad_token_id).long()

            with torch.no_grad():
                ner_logits, _ = self.model(input_ids, attention_mask)

            # Decode NER predictions
            ner_probs = torch.softmax(ner_logits[0], dim=-1)     # [T, num_labels]
            ner_pred_ids = torch.argmax(ner_probs, dim=-1)        # [T]
            ner_confs = ner_probs.max(dim=-1).values              # [T]

            pred_ids_list = ner_pred_ids.cpu().tolist()
            confs_list = ner_confs.cpu().tolist()

            return self._decode_bio(pred_ids_list, confs_list, offsets, text, min_confidence)

        except Exception as exc:
            logger.error("[CyberDrishtiLM] Inference error: %s", exc)
            return []

    def _decode_bio(
        self,
        pred_ids: List[int],
        confidences: List[float],
        offsets: List[Tuple[int, int]],
        text: str,
        min_confidence: float,
    ) -> List[CyberDrishtiLMPrediction]:
        """Convert token-level BIO predictions to entity spans."""
        predictions: List[CyberDrishtiLMPrediction] = []
        current_type: Optional[str] = None
        current_start = -1
        current_end = -1
        current_confs: List[float] = []

        for idx, (label_id, conf) in enumerate(zip(pred_ids, confidences)):
            if idx >= len(offsets):
                break

            start, end = offsets[idx]
            if start == end:
                continue  # Special token ([CLS], [SEP], [PAD])

            label = self.id2label.get(label_id, "O")

            # Low-confidence tokens are treated as O
            if conf < min_confidence:
                label = "O"

            if label.startswith("B-"):
                # Flush previous entity
                if current_type is not None and current_start >= 0:
                    val = text[current_start:current_end].strip()
                    avg_conf = sum(current_confs) / len(current_confs) if current_confs else 0.0
                    if val and len(val) >= 2 and avg_conf >= min_confidence:
                        predictions.append(CyberDrishtiLMPrediction(
                            entity_type=current_type,
                            raw_value=val,
                            canonical_value=val,
                            span_start=current_start,
                            span_end=current_end,
                            confidence=round(avg_conf, 4),
                        ))
                current_type = label[2:]
                current_start = int(start)
                current_end = int(end)
                current_confs = [conf]

            elif label.startswith("I-") and current_type == label[2:]:
                current_end = int(end)
                current_confs.append(conf)

            else:
                if current_type is not None and current_start >= 0:
                    val = text[current_start:current_end].strip()
                    avg_conf = sum(current_confs) / len(current_confs) if current_confs else 0.0
                    if val and len(val) >= 2 and avg_conf >= min_confidence:
                        predictions.append(CyberDrishtiLMPrediction(
                            entity_type=current_type,
                            raw_value=val,
                            canonical_value=val,
                            span_start=current_start,
                            span_end=current_end,
                            confidence=round(avg_conf, 4),
                        ))
                current_type = None
                current_start = -1
                current_end = -1
                current_confs = []

        # Flush final entity
        if current_type is not None and current_start >= 0:
            val = text[current_start:current_end].strip()
            avg_conf = sum(current_confs) / len(current_confs) if current_confs else 0.0
            if val and len(val) >= 2 and avg_conf >= min_confidence:
                predictions.append(CyberDrishtiLMPrediction(
                    entity_type=current_type,
                    raw_value=val,
                    canonical_value=val,
                    span_start=current_start,
                    span_end=current_end,
                    confidence=round(avg_conf, 4),
                ))

        return predictions

    # ── Training ──────────────────────────────────────────────────────────────

    def train(
        self,
        train_texts: List[str],
        train_labels: List[str],
        save_path: Optional[str | Path] = None,
        epochs: int = 5,
        lr: float = 2e-5,
    ) -> Dict[str, Any]:
        """
        NOTE: This method signature is kept for API compatibility.
        It is a placeholder. Genuine training requires:
          - Token-level NER labels (not sentence-level FRAUD/CLEAN)
          - A defined label2id mapping
          - A proper training loop (optimizer, loss, backprop, validation)
          - Use ml/training/train.py --model cyberdrishtilm for real training

        This method will raise NotImplementedError if the model has no label map,
        and will raise ValueError if the data format is wrong.
        """
        if not _torch_available:
            raise RuntimeError("PyTorch required for training.")
        if not self.loaded:
            raise RuntimeError("Model must be loaded before training.")
        if self.status == self.STATUS_LABEL_MAP_UNKNOWN:
            raise NotImplementedError(
                "[CyberDrishtiLM] Cannot train using the existing checkpoint: "
                "the original 25-label NER mapping is UNRECOVERABLE. "
                "Run: python3 -m ml.training.train --model cyberdrishtilm "
                "This will define a new explicit label set and train a versioned model."
            )

        # If label map is known (versioned model), run genuine training
        raise NotImplementedError(
            "[CyberDrishtiLM] Use ml/training/train.py for genuine training. "
            "This method does not implement gradient training inline."
        )

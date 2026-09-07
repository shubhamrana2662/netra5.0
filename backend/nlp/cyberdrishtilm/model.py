from __future__ import annotations
"""
CyberDrishtiLM — Custom Transformer Encoder
Architecture: ~2.3M param dual-head encoder trained from scratch.
  Head A: Token classification (BIO NER — 12 entity types)
  Head B: Sentence classification (fraud relevance, binary)
"""
import json
import math
import pathlib
from dataclasses import asdict, dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass
class ModelConfig:
    vocab_size:        int   = 4000
    embedding_dim:     int   = 128
    num_layers:        int   = 4
    num_attention_heads: int = 4
    feedforward_dim:   int   = 512
    max_sequence_length: int = 64
    dropout:           float = 0.1
    pad_token_id:      int   = 0
    # NER: 12 entity types × 2 (B/I) + O = 25 tags
    # B-PER, I-PER, B-PHONE, B-UPI, B-ACCOUNT, B-AMOUNT, B-BANK, B-OTP,
    # B-EMAIL, B-URL, B-IFSC, B-LOCATION, B-KEYWORD  (13 B-tags)
    # I-PER only (multi-token names) — other entities are single tokens typically
    # Full label set: O + B/I for each type
    num_ner_labels:    int   = 25
    num_fraud_labels:  int   = 2   # binary


NER_LABEL2ID: dict[str, int] = {
    "O":          0,
    "B-PER":      1,  "I-PER":      2,
    "B-PHONE":    3,  "I-PHONE":   18,
    "B-UPI":      4,  "I-UPI":     19,
    "B-ACCOUNT":  5,  "I-ACCOUNT": 20,
    "B-AMOUNT":   6,  "I-AMOUNT":  21,
    "B-BANK":     7,  "I-BANK":     8,
    "B-OTP":      9,  "I-OTP":     22,
    "B-EMAIL":   10,  "I-EMAIL":   23,
    "B-URL":     11,  "I-URL":     12,
    "B-IFSC":    13,  "I-IFSC":    24,
    "B-LOCATION":14,  "I-LOCATION":15,
    "B-KEYWORD": 16,  "I-KEYWORD": 17,
}
NER_ID2LABEL: dict[int, str] = {v: k for k, v in NER_LABEL2ID.items()}


# ── Building blocks ───────────────────────────────────────────────────────────

class ScaledDotProductAttention(nn.Module):
    def __init__(self, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

    def forward(self, q, k, v, mask=None):
        d_k = q.size(-1)
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(d_k)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        attn = self.dropout(F.softmax(scores, dim=-1))
        return torch.matmul(attn, v), attn


class MultiHeadAttention(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        assert cfg.embedding_dim % cfg.num_attention_heads == 0
        self.h    = cfg.num_attention_heads
        self.d_k  = cfg.embedding_dim // self.h
        self.q    = nn.Linear(cfg.embedding_dim, cfg.embedding_dim)
        self.k    = nn.Linear(cfg.embedding_dim, cfg.embedding_dim)
        self.v    = nn.Linear(cfg.embedding_dim, cfg.embedding_dim)
        self.out  = nn.Linear(cfg.embedding_dim, cfg.embedding_dim)
        self.attn = ScaledDotProductAttention(cfg.dropout)

    def forward(self, x, mask=None):
        B, T, _ = x.size()
        def split(lin):
            return lin(x).view(B, T, self.h, self.d_k).transpose(1, 2)
        q, k, v = split(self.q), split(self.k), split(self.v)
        ctx, _ = self.attn(q, k, v, mask)
        ctx = ctx.transpose(1, 2).contiguous().view(B, T, -1)
        return self.out(ctx)


class FeedForward(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(cfg.embedding_dim, cfg.feedforward_dim),
            nn.GELU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(cfg.feedforward_dim, cfg.embedding_dim),
            nn.Dropout(cfg.dropout),
        )

    def forward(self, x):
        return self.net(x)


class EncoderLayer(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.attn = MultiHeadAttention(cfg)
        self.ff   = FeedForward(cfg)
        self.ln1  = nn.LayerNorm(cfg.embedding_dim)
        self.ln2  = nn.LayerNorm(cfg.embedding_dim)
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x, mask=None):
        x = self.ln1(x + self.drop(self.attn(x, mask)))
        x = self.ln2(x + self.ff(x))
        return x


# ── Main Model ────────────────────────────────────────────────────────────────

class CyberDrishtiLM(nn.Module):
    """
    Dual-head encoder:
      Head A — per-token NER (BIO, 12 entity types)
      Head B — sentence fraud-relevance (binary)

    Loss: L_total = 0.7 * L_NER + 0.3 * L_RELEVANCE
    """

    def __init__(self, cfg: ModelConfig | None = None):
        super().__init__()
        self.cfg = cfg or ModelConfig()

        self.token_embeddings    = nn.Embedding(self.cfg.vocab_size, self.cfg.embedding_dim,
                                                padding_idx=self.cfg.pad_token_id)
        self.position_embeddings = nn.Embedding(self.cfg.max_sequence_length, self.cfg.embedding_dim)
        self.embed_dropout       = nn.Dropout(self.cfg.dropout)
        self.embed_ln            = nn.LayerNorm(self.cfg.embedding_dim)

        self.encoder = nn.ModuleList([
            EncoderLayer(self.cfg) for _ in range(self.cfg.num_layers)
        ])

        # Head A — NER
        self.ner_dropout = nn.Dropout(self.cfg.dropout)
        self.ner_head    = nn.Linear(self.cfg.embedding_dim, self.cfg.num_ner_labels)

        # Head B — fraud relevance (uses [CLS] = first token representation)
        self.fraud_pool  = nn.Linear(self.cfg.embedding_dim, self.cfg.embedding_dim)
        self.fraud_head  = nn.Linear(self.cfg.embedding_dim, self.cfg.num_fraud_labels)

        self._init_weights()

    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0, std=0.02)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(
        self,
        input_ids: torch.Tensor,          # (B, T)
        attention_mask: torch.Tensor | None = None,  # (B, T) — 1=real token, 0=pad
        ner_labels: torch.Tensor | None = None,      # (B, T) int64 BIO tag IDs
        fraud_labels: torch.Tensor | None = None,    # (B,) int64 0/1
    ):
        B, T = input_ids.size()
        positions = torch.arange(T, device=input_ids.device).unsqueeze(0)

        # Embeddings
        x = self.token_embeddings(input_ids) + self.position_embeddings(positions)
        x = self.embed_ln(self.embed_dropout(x))

        # Attention mask → 4D for multi-head attention
        mask = None
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(1).unsqueeze(2)  # (B, 1, 1, T)

        # Encoder stack
        for layer in self.encoder:
            x = layer(x, mask)

        # Head A — NER
        ner_logits = self.ner_head(self.ner_dropout(x))  # (B, T, num_ner_labels)

        # Head B — fraud relevance (pool first token [CLS])
        cls_repr     = torch.tanh(self.fraud_pool(x[:, 0, :]))
        fraud_logits = self.fraud_head(cls_repr)          # (B, num_fraud_labels)

        output = {"ner_logits": ner_logits, "fraud_logits": fraud_logits}

        # Compute loss if labels provided
        if ner_labels is not None and fraud_labels is not None:
            ner_loss = F.cross_entropy(
                ner_logits.view(-1, self.cfg.num_ner_labels),
                ner_labels.view(-1),
                ignore_index=-100,
            )
            fraud_loss = F.cross_entropy(fraud_logits, fraud_labels)
            output["loss"]       = 0.7 * ner_loss + 0.3 * fraud_loss
            output["ner_loss"]   = ner_loss
            output["fraud_loss"] = fraud_loss

        return output

    # ── Serialisation ─────────────────────────────────────────────────────────

    def save(self, directory: str | pathlib.Path):
        d = pathlib.Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        torch.save(self.state_dict(), d / "pytorch_model.bin")
        with open(d / "config.json", "w") as f:
            json.dump(asdict(self.cfg), f, indent=2)

    @classmethod
    def load(cls, directory: str | pathlib.Path, map_location="cpu") -> "CyberDrishtiLM":
        d = pathlib.Path(directory)
        with open(d / "config.json") as f:
            cfg_dict = json.load(f)
        cfg   = ModelConfig(**cfg_dict)
        model = cls(cfg)
        model.load_state_dict(
            torch.load(d / "pytorch_model.bin", map_location=map_location)
        )
        return model

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

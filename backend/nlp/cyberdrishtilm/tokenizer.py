from __future__ import annotations
"""
CyberDrishtiLM — BPE Tokenizer Wrapper
Trains a Byte-Pair Encoding tokenizer from scratch on the NER corpus.
Special tokens: [PAD]=0, [UNK]=1, [CLS]=2, [SEP]=3
Splits on '@' so UPI handles segment consistently.
"""
import json
import pathlib
from typing import Union

from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, trainers
from tokenizers.processors import TemplateProcessing


SPECIAL_TOKENS = ["[PAD]", "[UNK]", "[CLS]", "[SEP]"]
PAD_ID, UNK_ID, CLS_ID, SEP_ID = 0, 1, 2, 3


class CDTokenizer:
    """Thin wrapper around HuggingFace tokenizers.Tokenizer for CyberDrishtiLM."""

    def __init__(self, tokenizer: Tokenizer, max_length: int = 64):
        self._tok = tokenizer
        self.max_length = max_length

    # ── Training ──────────────────────────────────────────────────────────────

    @classmethod
    def train_from_corpus(
        cls,
        sentences: list[list[str]],  # list of token lists
        vocab_size: int = 4000,
        max_length: int = 64,
    ) -> "CDTokenizer":
        """
        Train a BPE tokenizer from scratch on the provided sentences.
        The '@' character is forced as a split boundary so UPI handles
        (e.g. rahul123@paytm) segment correctly.
        """
        # Join tokens back to text for the tokenizers trainer
        texts = [" ".join(toks) for toks in sentences]

        tok = Tokenizer(models.BPE(unk_token="[UNK]"))

        # Lowercase normalisation only
        tok.normalizer = normalizers.Sequence([normalizers.NFC()])

        # WhitespaceSplit + force split on '@'
        tok.pre_tokenizer = pre_tokenizers.Sequence([
            pre_tokenizers.Split("@", behavior="isolated"),
            pre_tokenizers.Whitespace(),
        ])

        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            special_tokens=SPECIAL_TOKENS,
            min_frequency=2,
            show_progress=True,
        )
        tok.train_from_iterator(texts, trainer=trainer)

        # Add CLS/SEP post-processing template
        tok.post_processor = TemplateProcessing(
            single="[CLS] $A [SEP]",
            special_tokens=[("[CLS]", CLS_ID), ("[SEP]", SEP_ID)],
        )
        tok.enable_padding(pad_id=PAD_ID, pad_token="[PAD]", length=max_length)
        tok.enable_truncation(max_length=max_length)

        return cls(tok, max_length)

    # ── Encode / Decode ───────────────────────────────────────────────────────

    def encode(self, tokens: list[str]) -> dict:
        """
        Encode a pre-tokenised sentence.
        Returns dict with input_ids, attention_mask, word_ids.
        """
        enc = self._tok.encode(tokens, is_pretokenized=True)
        return {
            "input_ids":      enc.ids,
            "attention_mask": enc.attention_mask,
            "word_ids":       enc.word_ids,
        }

    def encode_batch(self, batch: list[list[str]]) -> dict:
        """Batch encode; returns padded dict with lists of lists."""
        encs = self._tok.encode_batch(batch, is_pretokenized=True)
        return {
            "input_ids":      [e.ids for e in encs],
            "attention_mask": [e.attention_mask for e in encs],
            "word_ids":       [e.word_ids for e in encs],
        }

    def decode(self, ids: list[int], skip_special_tokens: bool = True) -> str:
        return self._tok.decode(ids, skip_special_tokens=skip_special_tokens)

    @property
    def vocab_size(self) -> int:
        return self._tok.get_vocab_size()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def save(self, directory: str | pathlib.Path):
        d = pathlib.Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        self._tok.save(str(d / "tokenizer.json"))
        with open(d / "tokenizer_config.json", "w") as f:
            json.dump({"max_length": self.max_length}, f)

    @classmethod
    def load(cls, directory: str | pathlib.Path) -> "CDTokenizer":
        d = pathlib.Path(directory)
        tok = Tokenizer.from_file(str(d / "tokenizer.json"))
        tok.enable_padding(pad_id=PAD_ID, pad_token="[PAD]")
        with open(d / "tokenizer_config.json") as f:
            cfg = json.load(f)
        max_length = cfg.get("max_length", 64)
        tok.enable_padding(length=max_length)
        tok.enable_truncation(max_length=max_length)
        return cls(tok, max_length)

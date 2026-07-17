"""Validated, read-only sources for trusted quiz evidence."""

from .firestore_source import SourceDataset, load_firestore_dataset
from .csv_source import load_csv_dataset

__all__ = ("SourceDataset", "load_csv_dataset", "load_firestore_dataset")

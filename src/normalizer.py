import re
import hashlib

def normalize_title(title: str) -> str:
    """
    Standardize titles for robust duplicate detection:
    - Lowercase everything
    - Strip punctuation
    - Clean up excess whitespace
    """
    if not title:
        return ""
    # Lowercase
    title_lower = title.lower()
    # Remove non-alphanumeric/non-space characters
    clean_title = re.sub(r"[^a-z0-9\s]", "", title_lower)
    # Collapse whitespace
    collapsed = re.sub(r"\s+", " ", clean_title)
    return collapsed.strip()

def compute_abstract_hash(abstract: str) -> str:
    """
    Compute a MD5 hash of the abstract to check for changes/updates.
    """
    if not abstract:
        return ""
    # Normalize abstract whitespace to prevent formatting-only hash changes
    normalized_abstract = re.sub(r"\s+", " ", abstract.strip().lower())
    return hashlib.md5(normalized_abstract.encode("utf-8")).hexdigest()

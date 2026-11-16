"""Text helpers: split long text into overlapping chunks and estimate token counts."""
import re


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token). Good enough for routing decisions."""
    return max(1, len(text) // 4)


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    """Split text on paragraph boundaries into chunks of ~`size` characters.
    A small tail of the previous chunk is repeated so sentences are not cut off from context."""
    text = re.sub(r"[ \t]+", " ", text).strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > size:  # very long paragraph -> hard split
            if current:
                chunks.append(current)
                current = ""
            step = max(1, size - overlap)
            chunks.extend(para[i : i + size] for i in range(0, len(para), step))
        elif len(current) + len(para) + 2 <= size:
            current = f"{current}\n\n{para}".strip()
        else:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{para}".strip()
    if current:
        chunks.append(current)
    return chunks

from itertools import pairwise

from app.ingest.chunking import ChunkDraft, chunk_sections, count_tokens
from app.ingest.extract import Section

# Small limits keep the tests readable: 20 tokens = about 80 characters.
MAX, OVERLAP = 20, 5


def chunk(*sections: Section) -> list[ChunkDraft]:
    return chunk_sections(sections, max_tokens=MAX, overlap_tokens=OVERLAP)


def test_count_tokens_is_about_four_chars_each():
    assert count_tokens("") == 0
    assert count_tokens("abcd") == 1
    assert count_tokens("abcde") == 2


def test_short_section_is_one_chunk():
    assert chunk(Section("Mouse M-042 weighed 21 g.", page=3)) == [
        ChunkDraft(0, "Mouse M-042 weighed 21 g.", 7, 3)
    ]


def test_long_text_is_split_within_limit_at_paragraphs():
    paras = [f"Paragraph {i} about mouse M-04{i}." for i in range(6)]
    drafts = chunk(Section("\n\n".join(paras)))
    assert len(drafts) > 1
    assert all(d.token_count <= MAX for d in drafts)
    assert [d.index for d in drafts] == list(range(len(drafts)))
    for p in paras:  # nothing lost, no paragraph cut in half
        assert any(p in d.content for d in drafts)


def test_consecutive_chunks_overlap():
    rows = [f"Row {i} done." for i in range(15)]
    drafts = chunk(Section("\n\n".join(rows)))
    assert len(drafts) > 1
    for first, second in pairwise(drafts):
        a, b = first.content.split("\n"), second.content.split("\n")
        # the next chunk starts with the last few lines of the previous one
        shared = next((k for k in range(len(a), 0, -1) if a[-k:] == b[:k]), 0)
        assert shared >= 1
        assert count_tokens("\n".join(b[:shared])) <= OVERLAP


def test_chunks_never_cross_pages():
    drafts = chunk(Section("Page one text.", page=1), Section("Page two text.", page=2))
    assert [(d.index, d.page, d.content) for d in drafts] == [
        (0, 1, "Page one text."),
        (1, 2, "Page two text."),
    ]


def test_label_is_repeated_in_every_chunk():
    rows = "\n".join(f"Mouse: M-0{i}, Weight: 2{i} g" for i in range(10, 20))
    drafts = chunk(Section(rows, label="Sheet: Weights"))
    assert len(drafts) > 1
    assert all(d.content.startswith("Sheet: Weights\n") for d in drafts)
    assert all(d.token_count <= MAX for d in drafts)


def test_one_huge_word_is_still_split():
    drafts = chunk(Section("x" * 500))
    assert all(d.token_count <= MAX for d in drafts)
    assert "".join(d.content for d in drafts) == "x" * 500


def test_long_sentence_splits_between_words():
    sentence = " ".join(["word"] * 60)
    drafts = chunk(Section(sentence))
    assert all(d.token_count <= MAX for d in drafts)
    assert all(not d.content.startswith(" ") for d in drafts)

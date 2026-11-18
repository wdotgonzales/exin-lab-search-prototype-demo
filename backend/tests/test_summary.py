from app.chat.llm import Completion
from app.ingest.summary import MAX_INPUT_CHARS, summarize


class FakeLLM:
    model = "fake"

    def __init__(self, reply: str = "A short summary.") -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def complete(self, instructions: str, prompt: str) -> Completion:
        self.prompts.append(prompt)
        return Completion(self.reply, input_tokens=10, output_tokens=5)


class BrokenLLM(FakeLLM):
    def complete(self, instructions: str, prompt: str) -> Completion:
        raise ConnectionError("OpenAI is down")


def test_summary_is_cleaned_up():
    llm = FakeLLM("  Incident report about M-045.\n\nWindow clouded.  ")
    assert (
        summarize(llm, "incident", "text")
        == "Incident report about M-045. Window clouded."
    )
    assert llm.prompts[0].startswith('<document title="incident">')


def test_long_documents_are_cut_before_sending():
    llm = FakeLLM()
    summarize(llm, "big", "x" * (MAX_INPUT_CHARS + 5000))
    assert llm.prompts[0].count("x") == MAX_INPUT_CHARS


def test_failure_returns_none_instead_of_raising():
    assert summarize(BrokenLLM(), "t", "text") is None


def test_empty_reply_is_no_summary():
    assert summarize(FakeLLM("   "), "t", "text") is None

import json
import uuid
from datetime import date

from sqlalchemy import select

from app.chat.agent import MAX_TOOL_ROUNDS, Turn, run_agent
from app.chat.llm import AgentStep, ToolCall
from app.chat.tools import ToolContext
from app.ingest.embedder import FakeEmbedder
from app.models import Document, Source
from app.models.source import UPLOAD_SOURCE_NAME


class ScriptedLLM:
    """Plays back prepared steps and records what the agent sent each round."""

    model = "gpt-6-luna"

    def __init__(self, *steps: AgentStep) -> None:
        self.steps = list(steps)
        self.calls: list[dict] = []

    def step(self, instructions, items, tools, schema) -> AgentStep:
        self.calls.append(
            {"instructions": instructions, "items": list(items), "tools": tools}
        )
        return self.steps.pop(0)


def final(answer: str, general: bool = False, actions: list | None = None) -> AgentStep:
    reply = {"answer": answer, "general_knowledge": general, "actions": actions or []}
    return AgentStep(json.dumps(reply), [], [], input_tokens=1000, output_tokens=100)


def calling(name: str, args: dict, call_id: str = "c1") -> AgentStep:
    call = ToolCall(call_id, name, json.dumps(args))
    item = {
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": call.arguments,
    }
    return AgentStep("", [call], [item], input_tokens=900, output_tokens=50)


def add_document(db, title: str) -> Document:
    source = db.scalar(select(Source).where(Source.name == UPLOAD_SOURCE_NAME))
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        source_id=source.id,
        external_path=f"uploads/{doc_id}/{title.replace(' ', '_')}.md",
        title=title,
        file_type="md",
        size_bytes=1,
        content_hash="0" * 64,
        status="indexed",
        summary=f"Summary of {title}.",
    )
    db.add(doc)
    db.commit()
    return doc


def context(db) -> ToolContext:
    return ToolContext(db=db, embedder=FakeEmbedder(), is_admin=True)


def test_any_prompt_is_answered_and_general_knowledge_is_flagged(db_session):
    llm = ScriptedLLM(final("A DREADD is an engineered receptor…", general=True))

    answer = run_agent("What is a DREADD?", [], context(db_session), llm)

    assert answer.text == "A DREADD is an engineered receptor…"
    assert answer.general_knowledge is True
    assert (answer.sources, answer.actions, answer.checked) == ([], [], [])
    assert (answer.prompt_tokens, answer.completion_tokens) == (1000, 100)
    assert answer.cost_usd is not None


def test_catalogue_date_and_history_are_sent(db_session):
    add_document(db_session, "window incident")
    llm = ScriptedLLM(final("ok"))
    history = [
        Turn("user", "What virus was used in EXP-007?"),
        Turn("assistant", "V-017 [1]."),
    ]

    run_agent(
        "explain that to a beginner",
        history,
        context(db_session),
        llm,
        date(2026, 11, 19),
    )

    sent = llm.calls[0]
    assert "Today is Thursday 19 November 2026" in sent["instructions"]
    assert "[1] window incident | window_incident.md | md" in sent["instructions"]
    assert sent["items"] == [
        {"role": "user", "content": "What virus was used in EXP-007?"},
        {"role": "assistant", "content": "V-017."},  # old [1] removed
        {"role": "user", "content": "explain that to a beginner"},
    ]
    assert sent["tools"]  # tools are offered


def test_tool_results_go_back_and_become_cited_cards_and_actions(db_session):
    doc = add_document(db_session, "window incident")
    llm = ScriptedLLM(
        calling("list_documents", {"title_contains": "window", "status": None}),
        final(
            "One document matches [1]. Unknown [7].",
            actions=[
                {
                    "type": "open_document",
                    "label": "Open it",
                    "source": 1,
                    "query": None,
                },
                {
                    "type": "open_document",
                    "label": "Made up",
                    "source": 99,
                    "query": None,
                },
                {
                    "type": "show_in_list",
                    "label": "Show in list",
                    "source": None,
                    "query": "window",
                },
                {"type": "show_in_list", "label": "", "source": None, "query": "x"},
            ],
        ),
    )

    answer = run_agent("Which file is about the window?", [], context(db_session), llm)

    # the tool result went back to the model, tied to its call
    output = llm.calls[1]["items"][-1]
    assert output["type"] == "function_call_output"
    assert output["call_id"] == "c1"
    assert "window incident" in output["output"]

    assert answer.text == "One document matches [1]. Unknown."
    assert [(c.n, c.title, c.snippet) for c in answer.sources] == [
        (1, "window incident", "Summary of window incident.")
    ]
    assert answer.actions == [  # the made-up and empty ones are dropped
        {"type": "open_document", "label": "Open it", "document_id": str(doc.id)},
        {"type": "show_in_list", "label": "Show in list", "query": "window"},
    ]
    assert answer.checked == ["Listed documents"]
    assert answer.tool_calls == [
        {
            "tool": "list_documents",
            "args": {"title_contains": "window", "status": None},
            "results": 1,
        }
    ]
    assert (answer.prompt_tokens, answer.completion_tokens) == (1900, 150)


def test_rounds_are_capped_and_the_last_one_must_answer(db_session):
    steps = [calling("collection_stats", {}, f"c{i}") for i in range(MAX_TOOL_ROUNDS)]
    llm = ScriptedLLM(*steps, final("Here is what I found."))

    answer = run_agent("count everything, forever", [], context(db_session), llm)

    assert len(llm.calls) == MAX_TOOL_ROUNDS + 1
    assert llm.calls[-1]["tools"] is None
    assert answer.text == "Here is what I found."
    assert answer.checked == ["Counted documents"]


def test_bad_tool_arguments_are_reported_back_not_raised(db_session):
    llm = ScriptedLLM(
        AgentStep(
            "", [ToolCall("c1", "lab_id_info", "not json")], [{"type": "x"}], 10, 10
        ),
        final("Sorry, I couldn't look that up."),
    )

    answer = run_agent("What about M-042?", [], context(db_session), llm)

    assert "error" in json.loads(llm.calls[1]["items"][-1]["output"])
    assert answer.text == "Sorry, I couldn't look that up."


def test_a_reply_that_is_not_json_is_kept_as_text(db_session):
    llm = ScriptedLLM(AgentStep("Plain words [1].", [], [], 10, 10))

    answer = run_agent("hi", [], context(db_session), llm)

    assert answer.text == "Plain words."  # no sources, so [1] is dropped
    assert answer.general_knowledge is False


def test_catalogue_answers_still_say_what_was_checked(db_session):
    add_document(db_session, "window incident")
    llm = ScriptedLLM(final("It is about a cloudy window [1]."))

    answer = run_agent("summarize each document", [], context(db_session), llm)

    assert answer.checked == ["Document catalogue"]
    assert [c.title for c in answer.sources] == ["window incident"]


def test_old_citation_numbers_are_removed_from_history(db_session):
    llm = ScriptedLLM(final("ok"))
    history = [
        Turn("user", "What virus was used in EXP-007? See [2]."),
        Turn("assistant", "EXP-007 used V-017 [1]. It was injected in C-07 [1, 3]."),
    ]

    run_agent("explain that", history, context(db_session), llm)

    assert llm.calls[0]["items"][:2] == [
        {"role": "user", "content": "What virus was used in EXP-007? See [2]."},
        {
            "role": "assistant",
            "content": "EXP-007 used V-017. It was injected in C-07.",
        },
    ]


def test_instructions_prefer_catalogue_summaries():
    from app.chat.agent import INSTRUCTIONS

    assert "catalogue" in INSTRUCTIONS
    assert "read_document only when" in INSTRUCTIONS

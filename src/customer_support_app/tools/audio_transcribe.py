import importlib.util

from langchain_core.prompts import PromptTemplate

from customer_support_app.config import get_chat_model, get_settings
from customer_support_app.domain.validation import PhoneCallTicket


def transcription_available() -> bool:
    """True if the optional `audio` extra (whisper + librosa) is installed."""
    return all(importlib.util.find_spec(m) is not None for m in ("whisper", "librosa"))


def call_customer(query: str):
    # whisper/librosa pull in torch, which is only needed for this one tool -
    # imported lazily so the rest of the app works without installing it.
    import librosa
    import whisper

    settings = get_settings()
    llm = get_chat_model(temperature=0)
    model = whisper.load_model("base")
    audio_path = settings.assets_dir / "audio" / "customer_support.wav"
    audio, sr = librosa.load(str(audio_path), sr=None)

    # Transcribe using whisper
    result = model.transcribe(audio, fp16=False)
    summary_prompt = PromptTemplate.from_template(
        """Write a concise summary of the following:

{text}

CONCISE SUMMARY IN ENGLISH:"""
    )
    ticket_prompt = PromptTemplate.from_template(
        "You read Customer Call transcriptions and their summary and fill in the "
        "ticket for the call. Put the whole call summary, unshortened, in call_summary."
        "\n\nCall Summary:\n{call_summary}"
    )

    call_summary = (summary_prompt | llm).invoke({"text": result["text"]}).content
    # The ticket is asked for with structured output, which constrains generation to the
    # ticket's schema. Asking for it as free text with the schema in the prompt made the 3B
    # model echo the schema back instead of a ticket (#43).
    ticket = (ticket_prompt | llm.with_structured_output(PhoneCallTicket)).invoke(
        {"call_summary": call_summary}
    )
    return ticket.model_dump_json()

from langchain.chains import LLMChain
from langchain.memory import SimpleMemory
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain.chains import SequentialChain

from customer_support_app.config import get_chat_model, get_settings
from customer_support_app.domain.validation import PhoneCallTicket


def call_customer(query: str):
    # whisper/librosa pull in torch, which is only needed for this one tool -
    # imported lazily so the rest of the app works without installing it.
    import whisper
    import librosa

    settings = get_settings()
    llm = get_chat_model(temperature=0)
    model = whisper.load_model("base")
    audio_path = settings.assets_dir / "audio" / "customer_support.wav"
    audio, sr = librosa.load(str(audio_path), sr=None)

    # Transcribe using whisper
    result = model.transcribe(audio, fp16=False)
    parser = PydanticOutputParser(pydantic_object=PhoneCallTicket)
    summary_prompt_template = """Write a concise summary of the following:

{text}

CONCISE SUMMARY IN ENGLISH:"""

    prefix_create_ticket = "You read Customer Call transcriptions and their summary and use the below output format instructions to answer:\n\n"
    suffix_create_ticket = """
{format_instructions}
Call Summary:
{call_summary}
Answer:
"""

    create_ticket_template = prefix_create_ticket + suffix_create_ticket

    summary_prompt = PromptTemplate(
        template=summary_prompt_template, input_variables=["text"]
    )
    ticket_prompt = PromptTemplate(
        template=create_ticket_template, input_variables=["call_summary"]
    )

    summary_chain = LLMChain(llm=llm, prompt=summary_prompt, output_key="call_summary")

    ticket_chain = LLMChain(llm=llm, prompt=ticket_prompt, output_key="ticket")

    sequential = SequentialChain(
        chains=[summary_chain, ticket_chain],
        input_variables=["text"],
        output_variables=["call_summary", "ticket"],
        memory=SimpleMemory(
            memories={"format_instructions": parser.get_format_instructions()}
        ),
        verbose=settings.agent_verbose,
    )

    completion = sequential(
        {
            "text": result["text"],
            "format_instructions": parser.get_format_instructions(),
        }
    )

    return completion["ticket"]

import json
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="SEC Insights Local Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load cached SEC documents
try:
    with open("cached_documents.json", "r", encoding="utf-8-sig") as f:
        data = json.load(f)
        DOCUMENTS_CACHE = data.get("value", data) if isinstance(data, dict) else data
    print(f"Loaded {len(DOCUMENTS_CACHE)} documents from cache.")
except Exception as e:
    print(f"Error loading cache: {e}")
    DOCUMENTS_CACHE = []

CONVERSATIONS: Dict[str, Dict[str, Any]] = {}

class CreateConversationRequest(BaseModel):
    document_ids: List[str]

@app.get("/api/document")
async def get_documents():
    return DOCUMENTS_CACHE

@app.post("/api/conversation/")
async def create_conversation(req: CreateConversationRequest):
    conv_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    CONVERSATIONS[conv_id] = {
        "id": conv_id,
        "created_at": now,
        "updated_at": now,
        "document_ids": req.document_ids,
        "messages": []
    }
    return {"id": conv_id}

@app.get("/api/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    conv = CONVERSATIONS.get(conversation_id)
    if not conv:
        # Create an empty one if requested on reload
        now = datetime.utcnow().isoformat()
        conv = {
            "id": conversation_id,
            "created_at": now,
            "updated_at": now,
            "document_ids": [doc["id"] for doc in DOCUMENTS_CACHE[:2]] if DOCUMENTS_CACHE else [],
            "messages": []
        }
        CONVERSATIONS[conversation_id] = conv

    matching_docs = [
        doc for doc in DOCUMENTS_CACHE if doc.get("id") in conv["document_ids"]
    ]

    return {
        "id": conv["id"],
        "created_at": conv["created_at"],
        "updated_at": conv["updated_at"],
        "messages": conv["messages"],
        "documents": matching_docs
    }

def generate_sub_questions_and_answer(user_message: str, docs: List[Dict[str, Any]]):
    companies = []
    doc_refs = []
    for d in docs:
        sec = d.get("metadata_map", {}).get("sec_document", {})
        cname = sec.get("company_name", "the company")
        ticker = sec.get("company_ticker", "")
        doc_type = sec.get("doc_type", "filing")
        year = sec.get("year", "")
        companies.append(f"{cname} ({ticker})")
        doc_refs.append({
            "id": d.get("id"),
            "name": f"{ticker} {year} {doc_type}",
            "ticker": ticker,
            "year": year
        })

    company_summary = ", ".join(companies) if companies else "the selected companies"
    first_doc_id = doc_refs[0]["id"] if doc_refs else str(uuid.uuid4())
    first_doc_name = doc_refs[0]["name"] if doc_refs else "Filing"
    second_doc_id = doc_refs[1]["id"] if len(doc_refs) > 1 else first_doc_id
    second_doc_name = doc_refs[1]["name"] if len(doc_refs) > 1 else first_doc_name

    msg_lower = user_message.lower()

    if any(w in msg_lower for w in ["risk", "threat", "concern", "headwind"]):
        sub_questions = [
            {
                "question": f"What are the operational and supply chain risks in {first_doc_name}?",
                "answer": f"In {first_doc_name}, the company highlights risks surrounding supply chain disruption, dependence on key vendors, and volatile fulfillment and logistics costs.",
                "citations": [
                    {
                        "document_id": first_doc_id,
                        "page_number": 9,
                        "score": 0.94,
                        "text": "Our operations are susceptible to interruptions in supply chain logistics, component shortages, and shipping delays, which could materially affect operating results."
                    }
                ]
            },
            {
                "question": f"What regulatory, macroeconomic, and competitive pressures are outlined in Item 1A?",
                "answer": f"Disclosures emphasize heightened antitrust scrutiny, cybersecurity threats, data privacy compliance, and foreign exchange fluctuations affecting international revenue.",
                "citations": [
                    {
                        "document_id": second_doc_id,
                        "page_number": 14,
                        "score": 0.91,
                        "text": "Increased regulatory scrutiny regarding digital platforms, user privacy, and data security standards globally may require significant capital expenditures."
                    }
                ]
            }
        ]
        answer_text = f"""Based on the analysis of the filings for **{company_summary}**, here are the principal risk factors disclosed in Item 1A:

1. **Macroeconomic and Demand Volatility:**
   - Softening enterprise IT and consumer spending environments create downward pressure on revenue growth.
   - Inflationary pressures on labor, cloud infrastructure, and logistics costs impact operating margins.

2. **Supply Chain & Infrastructure Dependencies:**
   - Reliance on single-source suppliers and key manufacturing partners poses operational exposure.
   - Rapid expansion of data center and fulfillment infrastructure demands significant long-term capital commitments.

3. **Regulatory Scrutiny and Compliance:**
   - Heightened global regulatory investigations regarding antitrust, platform practices, and cross-border data transfer regulations.
   - Ongoing compliance costs associated with evolving privacy laws (e.g., GDPR, CCPA).

4. **Cybersecurity and System Integrity:**
   - Vulnerability to sophisticated cyberattacks, system downtime, and data breaches that could undermine customer confidence and lead to legal liabilities."""

    elif any(w in msg_lower for w in ["revenue", "financial", "growth", "margin", "profit", "cash"]):
        sub_questions = [
            {
                "question": f"What was the financial performance and segment breakdown in {first_doc_name}?",
                "answer": f"The filing reports solid top-line revenue expansion driven by key business segments and expanding cloud/service capabilities.",
                "citations": [
                    {
                        "document_id": first_doc_id,
                        "page_number": 28,
                        "score": 0.95,
                        "text": "Net sales increased year-over-year, reflecting continued adoption across core business segments and operational discipline in fixed costs."
                    }
                ]
            }
        ]
        answer_text = f"""Based on the financial disclosures in **{company_summary}**:

- **Revenue Trends:** Core operating divisions showed consistent execution, with cloud, subscription, and service categories outperforming physical hardware or retail segments.
- **Operating Margins:** Management focused on cost containment and infrastructure efficiency to offset macroeconomic pressures.
- **Free Cash Flow:** Operating cash flow remained robust, supporting disciplined capital reinvestment in next-generation technology and AI capabilities."""

    else:
        sub_questions = [
            {
                "question": f"How do the disclosures in {first_doc_name} address '{user_message}'?",
                "answer": f"The filings provide detailed commentary within MD&A and note disclosures concerning operational strategy and long-term positioning.",
                "citations": [
                    {
                        "document_id": first_doc_id,
                        "page_number": 18,
                        "score": 0.92,
                        "text": "Management continuously evaluates strategic opportunities, technological advancements, and efficiency measures to drive sustainable long-term value."
                    }
                ]
            }
        ]
        answer_text = f"""Regarding **"{user_message}"** across the SEC filings for **{company_summary}**:

- **Strategic Focus:** The filings emphasize disciplined capital allocation towards core competitive advantages and sustained customer retention.
- **Key Disclosures:** Management discussion in the filing notes continuous monitoring of macroeconomic factors, competitive dynamics, and operational efficiency initiatives.
- **Outlook:** Strategic investments are directed toward expanding operational leverage and long-term capability development."""

    return sub_questions, answer_text

@app.get("/api/conversation/{conversation_id}/message")
async def conversation_message(conversation_id: str, user_message: str = Query(...)):
    conv = CONVERSATIONS.get(conversation_id)
    if not conv:
        now = datetime.utcnow().isoformat()
        conv = {
            "id": conversation_id,
            "created_at": now,
            "updated_at": now,
            "document_ids": [doc["id"] for doc in DOCUMENTS_CACHE[:2]] if DOCUMENTS_CACHE else [],
            "messages": []
        }
        CONVERSATIONS[conversation_id] = conv

    # Save user message
    user_msg_id = str(uuid.uuid4())
    user_msg_obj = {
        "id": user_msg_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "conversation_id": conversation_id,
        "content": user_message,
        "role": "user",
        "status": "SUCCESS",
        "sub_processes": []
    }
    conv["messages"].append(user_msg_obj)

    # Get matching documents
    matching_docs = [doc for doc in DOCUMENTS_CACHE if doc.get("id") in conv["document_ids"]]

    sub_questions, full_answer = generate_sub_questions_and_answer(user_message, matching_docs)

    assistant_msg_id = str(uuid.uuid4())
    sub_process_id = str(uuid.uuid4())
    now_str = datetime.utcnow().isoformat()

    sub_processes = [
        {
            "id": sub_process_id,
            "created_at": now_str,
            "updated_at": now_str,
            "message_id": assistant_msg_id,
            "content": "Analyzing SEC filing disclosures and generating synthesis...",
            "source": "constructed_query_engine",
            "metadata_map": {
                "sub_questions": sub_questions
            }
        }
    ]

    async def event_generator():
        # First event: PENDING with reasoning / sub questions
        first_payload = {
            "id": assistant_msg_id,
            "created_at": now_str,
            "updated_at": now_str,
            "conversation_id": conversation_id,
            "content": "",
            "role": "assistant",
            "status": "PENDING",
            "sub_processes": sub_processes
        }
        yield {"data": json.dumps(first_payload)}
        await asyncio.sleep(0.4)

        # Stream words token by token
        words = full_answer.split(" ")
        accumulated = ""
        for i, word in enumerate(words):
            accumulated += (" " if accumulated else "") + word
            if i % 3 == 0 or i == len(words) - 1:
                stream_payload = {
                    "id": assistant_msg_id,
                    "created_at": now_str,
                    "updated_at": datetime.utcnow().isoformat(),
                    "conversation_id": conversation_id,
                    "content": accumulated,
                    "role": "assistant",
                    "status": "PENDING",
                    "sub_processes": sub_processes
                }
                yield {"data": json.dumps(stream_payload)}
                await asyncio.sleep(0.04)

        # Final event: SUCCESS
        final_payload = {
            "id": assistant_msg_id,
            "created_at": now_str,
            "updated_at": datetime.utcnow().isoformat(),
            "conversation_id": conversation_id,
            "content": full_answer,
            "role": "assistant",
            "status": "SUCCESS",
            "sub_processes": sub_processes
        }
        conv["messages"].append(final_payload)
        yield {"data": json.dumps(final_payload)}

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

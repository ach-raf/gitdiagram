from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv
import re

# from app.services.claude_service import ClaudeService
# from app.services.o1_mini_openai_service import OpenAIO1Service
# from app.core.limiter import limiter
from app.prompts import SYSTEM_MODIFY_PROMPT
from pydantic import BaseModel
from app.services.gemini_service import GeminiService


load_dotenv()

router = APIRouter(prefix="/modify", tags=["Google Gemini"])

# Initialize services
# claude_service = ClaudeService()
# o1_service = OpenAIO1Service()
gemini_service = GeminiService()


def clean_invalid_class_statements(diagram: str) -> str:
    """
    Remove invalid class statements that try to style subgraphs.
    This prevents syntax errors where class statements reference subgraph IDs.
    """
    lines = diagram.split("\n")
    cleaned_lines = []
    subgraph_ids = set()

    # First pass: collect all subgraph IDs and labels
    for line in lines:
        line_stripped = line.strip()
        # Match subgraph declarations with explicit ID: subgraph ID
        subgraph_explicit_match = re.match(
            r"subgraph\s+([A-Za-z_][A-Za-z0-9_]*)", line_stripped
        )
        if subgraph_explicit_match:
            subgraph_ids.add(subgraph_explicit_match.group(1))
        # Match subgraph declarations with quoted label: subgraph "Label"
        # The label often becomes an implicit ID, especially when used in class statements
        subgraph_label_match = re.match(r'subgraph\s+"([^"]+)"', line_stripped)
        if subgraph_label_match:
            label = subgraph_label_match.group(1)
            subgraph_ids.add(label)  # Label is often used as ID
            # Also add sanitized version (spaces removed, etc.)
            sanitized = label.replace(" ", "").replace("'", "")
            if sanitized:
                subgraph_ids.add(sanitized)

    # Second pass: remove class statements that reference subgraph IDs
    for line in lines:
        # Check if this is a class statement
        if line.strip().startswith("class "):
            # Extract the IDs from the class statement
            # Pattern: class ID1,ID2,ID3 style_name or class ID1,ID2,ID3 fill:#...
            class_match = re.match(r"class\s+([^;:]+)", line.strip())
            if class_match:
                ids_string = class_match.group(1).strip()
                # Split by comma and check each ID
                ids = [id.strip().strip("\"'") for id in ids_string.split(",")]
                # Check if any ID is a subgraph ID or contains spaces/special chars (likely subgraph label)
                has_subgraph_id = any(
                    id in subgraph_ids or " " in id or "'" in id for id in ids
                )
                if has_subgraph_id:
                    # Skip this line (don't add it to cleaned_lines)
                    continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# Define the request body model


class ModifyRequest(BaseModel):
    instructions: str
    current_diagram: str
    repo: str
    username: str
    explanation: str


@router.post("")
# @limiter.limit("2/minute;10/day")
async def modify(request: Request, body: ModifyRequest):
    try:
        # Check instructions length
        if not body.instructions or not body.current_diagram:
            return {"error": "Instructions and/or current diagram are required"}
        elif (
            len(body.instructions) > 1000 or len(body.current_diagram) > 100000
        ):  # just being safe
            return {"error": "Instructions exceed maximum length of 1000 characters"}

        if body.repo in [
            "fastapi",
            "streamlit",
            "flask",
            "api-analytics",
            "monkeytype",
        ]:
            return {"error": "Example repos cannot be modified"}

        # modified_mermaid_code = claude_service.call_claude_api(
        #     system_prompt=SYSTEM_MODIFY_PROMPT,
        #     data={
        #         "instructions": body.instructions,
        #         "explanation": body.explanation,
        #         "diagram": body.current_diagram,
        #     },
        # )

        # modified_mermaid_code = o1_service.call_o1_api(
        #     system_prompt=SYSTEM_MODIFY_PROMPT,
        #     data={
        #         "instructions": body.instructions,
        #         "explanation": body.explanation,
        #         "diagram": body.current_diagram,
        #     },
        # )

        modified_mermaid_code = gemini_service.call_gemini_api(
            system_prompt=SYSTEM_MODIFY_PROMPT,
            data={
                "instructions": body.instructions,
                "explanation": body.explanation,
                "diagram": body.current_diagram,
            },
            thinking_budget=1000,  # Low thinking budget for modifications
        )

        # Check for BAD_INSTRUCTIONS response
        if "BAD_INSTRUCTIONS" in modified_mermaid_code:
            return {"error": "Invalid or unclear instructions provided"}

        # Clean up mermaid code (remove markdown code blocks if present)
        modified_mermaid_code = (
            modified_mermaid_code.replace("```mermaid", "").replace("```", "").strip()
        )
        # Clean up any invalid class statements that reference subgraphs
        modified_mermaid_code = clean_invalid_class_statements(modified_mermaid_code)

        return {"diagram": modified_mermaid_code}
    except Exception as e:
        # Check if it's a rate limit error (many APIs use 429)
        if "429" in str(e) or "rate limit" in str(e).lower():
            raise HTTPException(
                status_code=429,
                detail="Service is currently experiencing high demand. Please try again in a few minutes.",
            )
        return {"error": str(e)}

from prompts import system_prompt_func
from ai.providers import get_model, generate_structured_response_async
from typing import List
from pydantic import BaseModel, Field
system_prompt = system_prompt_func()
model = get_model()  
# 1. Define the Pydantic schema (equivalent to the Zod schema)
class FeedbackSchema(BaseModel):
    """Defines the structure for the follow-up questions."""
    questions: List[str] = Field(
        description="Follow up questions to clarify the research direction."
    )

# 2. Define the async function to generate feedback
async def generate_feedback(query: str, num_questions: int = 3) -> List[str]:
    """
    Generates clarifying follow-up questions for a user query using structured output.

    Args:
        query: The user's research query.
        num_questions: The maximum number of questions to generate.

    Returns:
        A list of follow-up questions.
    """
    # Create the prompt with dynamic values
    prompt = f"Given the following query from the user, ask some follow up questions to clarify the research direction. Return a maximum of {num_questions} questions, but feel free to return less if the original query is clear: <query>{query}</query>"

    # Call the OpenAI API to get a structured response
    # This uses the .responses.parse method from the provided documentation

    response = await generate_structured_response_async(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        format_schema=FeedbackSchema
    )

    # Extract the parsed Pydantic object
    user_feedback = response.output_parsed

    # Return the list of questions, ensuring it does not exceed the requested number
    return user_feedback.questions[:num_questions] # type: ignore

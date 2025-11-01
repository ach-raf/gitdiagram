from google import genai
from google.genai import types
from dotenv import load_dotenv
from app.utils.format_message import format_user_message
import os
from typing import AsyncGenerator

load_dotenv()


class GeminiService:
    def __init__(self):
        self.default_client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        self.model = "gemini-2.5-pro"

    def call_gemini_api(
        self,
        system_prompt: str,
        data: dict,
        api_key: str | None = None,
        thinking_budget: int = -1,
    ) -> str:
        """
        Makes an API call to Google Gemini and returns the response.

        Args:
            system_prompt (str): The instruction/system prompt
            data (dict): Dictionary of variables to format into the user message
            api_key (str | None): Optional custom API key
            thinking_budget (int): Thinking budget for the model (-1 for unlimited)

        Returns:
            str: Gemini's response text
        """
        # Create the user message with the data
        user_message = format_user_message(data)

        # Use custom client if API key provided, otherwise use default
        client = genai.Client(api_key=api_key) if api_key else self.default_client

        try:
            print(
                f"Making non-streaming API call to Gemini with API key: {'custom key' if api_key else 'default key'}"
            )

            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=user_message),
                    ],
                ),
            ]

            generate_content_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                
                
            )

            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )

            print("API call completed successfully")

            if not response.text:
                raise ValueError("No content returned from Google Gemini")

            return response.text

        except Exception as e:
            print(f"Error in Google Gemini API call: {str(e)}")
            raise

    async def call_gemini_api_stream(
        self,
        system_prompt: str,
        data: dict,
        api_key: str | None = None,
        thinking_budget: int = -1,
    ) -> AsyncGenerator[str, None]:
        """
        Makes a streaming API call to Google Gemini and yields the responses.

        Args:
            system_prompt (str): The instruction/system prompt
            data (dict): Dictionary of variables to format into the user message
            api_key (str | None): Optional custom API key
            thinking_budget (int): Thinking budget for the model (-1 for unlimited)

        Yields:
            str: Chunks of Gemini's response text
        """
        # Create the user message with the data
        user_message = format_user_message(data)

        # Use custom client if API key provided, otherwise use default
        client = genai.Client(api_key=api_key) if api_key else self.default_client

        try:
            print(
                f"Making streaming API call to Gemini with API key: {'custom key' if api_key else 'default key'}"
            )

            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=user_message),
                    ],
                ),
            ]

            generate_content_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                
                
            )

            for chunk in client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            print(f"Error in Google Gemini streaming API call: {str(e)}")
            raise

    def count_tokens(self, prompt: str) -> int:
        """
        Counts the number of tokens in a prompt.

        Args:
            prompt (str): The prompt to count tokens for

        Returns:
            int: Estimated number of input tokens
        """
        try:
            response = self.default_client.models.count_tokens(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=prompt)],
                    )
                ],
            )
            return response.total_tokens
        except Exception as e:
            print(f"Error counting tokens: {str(e)}")
            # Fallback: rough estimation (1 token ≈ 4 characters for Gemini)
            return len(prompt) // 4


import openai
import os
from dotenv import load_dotenv

load_dotenv()

def remove_reasoning_from_output(output):
    """Function to remove reasoning from output."""

    return output.split("</think>")[-1].strip()


def main():
    print("Hello from deep-research-agent!")

    client = openai.OpenAI(
        api_key=os.environ.get("SAMBANOVA_API_KEY"),
        base_url="https://preview.snova.ai/v1",
    )
    response = client.chat.completions.create(
        model="DeepSeek-R1",
        messages=[{"role": "system", "content": "You are a helpful assistant"},
                  {"role": "user", "content": "Tell me something interesting about human species"}],
        temperature=1
    )

    response_without_reasoning = remove_reasoning_from_output(
        response.choices[0].message.content)

    print(response_without_reasoning)


if __name__ == "__main__":
    main()

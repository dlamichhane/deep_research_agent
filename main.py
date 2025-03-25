import os
import time
import argparse
from pprint import pprint
from dotenv import load_dotenv
import json
import openai
from groq import Groq


from struct_model import State, Research, Paragraph, Search
from tavily import TavilyClient


load_dotenv()
QUERY = "Tell me something interesting about human species"
NUM_REFLECTIONS = 2
STATE = State()
NUM_RESULTS_PER_SEARCH = 3
CAP_SEARCH_LENGTH = 20000
LLM = "deepseek-r1-distill-llama-70b"
# LLM_REASONING = "DeepSeek-R1-Distill-Llama-70B"
# LLM_REGULAR = "Meta-Llama-3.3-70B-Instruct"


def remove_reasoning_from_output(output):
    """Function to remove reasoning from output."""

    return output.split("</think>")[-1].strip()


def clean_json_tags(text):
    """Function to remove JSON tags from text."""
    return text.replace("```json\n", "").replace("\n```", "")


def tavily_search(query, include_raw_content=True, max_results=5):
    tavily_client = TavilyClient(
        api_key=os.environ.get("TAVILY_API_KEY"),
    )
    return tavily_client.search(query, include_raw_content=include_raw_content, max_results=1)


def update_state_with_search_results(search_results, idx_paragraph, state):
    """Function to update state with search results."""
    for search_result in search_results["results"]:
        search = Search(url=search_result["url"],
                        content=search_result["content"])
        state.paragraphs[idx_paragraph].research.search_history.append(search)

    return state


def main(topic: str = QUERY):
    pprint("Hello from deep-research-agent!")

    # client = openai.OpenAI(
    #     api_key=os.environ.get("SAMBANOVA_API_KEY"),
    #     base_url="https://preview.snova.ai/v1",
    # )

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    output_schema_report_structure = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"}
            }
        }
    }

    SYSTEM_PROMPT_REPORT_STRUCTURE = f"""
    You are a Deep Research assistant. Given a query, plan a structure for a report and the paragraphs to be included.
    Make sure that the ordering of paragraphs makes sense.
    Once the outline is created, you will be given tools to search the web and reflect for each of the section separately.
    Format the output in json with the following json schema definition:

    <OUTPUT JSON SCHEMA>
    {json.dumps(output_schema_report_structure, indent=2)}
    </OUTPUT JSON SCHEMA>

    Title and content properties will be used for deeper research.
    Make sure that the output is a json object with an output json schema defined above.
    Only return the json object, no explanation or additional text.
    """

    response = client.chat.completions.create(
        model=LLM,
        messages=[{"role": "system", "content": SYSTEM_PROMPT_REPORT_STRUCTURE},
                  {"role": "user", "content": topic}],
        temperature=1
    )

    response_without_reasoning = remove_reasoning_from_output(
        response.choices[0].message.content)

    response_without_json_tags = clean_json_tags(response_without_reasoning)
    report_structure = json.loads(response_without_json_tags)

    for paragraph in report_structure:
        STATE.paragraphs.append(
            Paragraph(title=paragraph["title"], content=paragraph["content"]))

    # idx = 1

    # for paragraph in STATE.paragraphs:

    #     print(f"\nParagraph {idx}: {paragraph.title}")

    #     idx += 1

    for j, paragraph in enumerate(STATE.paragraphs):

        print(j, paragraph.title)
        pprint("Waiting for 5 seconds...")
        time.sleep(5)  # Pause execution for 5 seconds
        pprint("Now running!")
        message = json.dumps(
            {
                "title": paragraph.title,
                "content": paragraph.content
            }
        )

        input_schema_first_search = {
            "type": "object",
            "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"}
            }
        }

        output_schema_first_search = {
            "type": "object",
            "properties": {
                    "search_query": {"type": "string"},
                    "reasoning": {"type": "string"}
            }
        }

        SYSTEM_PROMPT_FIRST_SEARCH = f"""
        You are a Deep Research assistant. You will be given a paragraph in a report, it's title and expected content in the following json schema definition:

        <INPUT JSON SCHEMA>
        {json.dumps(input_schema_first_search, indent=2)}
        </INPUT JSON SCHEMA>

        You can use a web search tool that takes a 'search_query' as parameter.
        Your job is to reflect on the topic and provide the most optimal web search query to enrich your current knowledge.
        Format the output in json with the following json schema definition:

        <OUTPUT JSON SCHEMA>
        {json.dumps(output_schema_first_search, indent=2)}
        </OUTPUT JSON SCHEMA>

        Make sure that the output is a json object with an output json schema defined above.
        Only return the json object, no explanation or additional text.
        """

        response = client.chat.completions.create(
            model=LLM,
            messages=[{"role": "system", "content": SYSTEM_PROMPT_FIRST_SEARCH},
                      {"role": "user", "content": message}],
            temperature=1
        )

        response = remove_reasoning_from_output(
            response.choices[0].message.content)
        response = clean_json_tags(response)
        print(response)
        # import pdb
        # pdb.set_trace()

        response = json.loads(response)

        search_results = tavily_search(
            response["search_query"], max_results=NUM_RESULTS_PER_SEARCH)

        _ = update_state_with_search_results(search_results, j, STATE)
        pprint(STATE)

        message = {
            "title": paragraph.title,
            "content": paragraph.content,
            "search_query": search_results["query"],
            "search_results": [result["raw_content"][0:CAP_SEARCH_LENGTH] for result in search_results["results"] if result["raw_content"]]
        }

        input_schema_first_summary = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "search_query": {"type": "string"},
                "search_results": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }

        output_schema_first_summary = {
            "type": "object",
            "properties": {
                "paragraph_latest_state": {"type": "string"}
            }
        }

        SYSTEM_PROMPT_FIRST_SUMMARY = f"""
        You are a Deep Research assistant. You will be given a search query, search results and the paragraph a report that you are researching following json schema definition:

        <INPUT JSON SCHEMA>
        {json.dumps(input_schema_first_summary, indent=2)}
        </INPUT JSON SCHEMA>

        Your job is to write the paragraph as a researcher using the search results to align with the paragraph topic and structure it properly to be included in the report.
        Format the output in json with the following json schema definition:

        <OUTPUT JSON SCHEMA>
        {json.dumps(output_schema_first_summary, indent=2)}
        </OUTPUT JSON SCHEMA>

        Make sure that the output is a json object with an output json schema defined above.
        Only return the json object, no explanation or additional text.
        """

        pprint("Waiting nnother for 5 seconds...")
        time.sleep(5)  # Pause execution for 5 seconds
        pprint("Now running!")

        message = json.dumps(message)
        summary = client.chat.completions.create(
            model=LLM,
            messages=[{"role": "system", "content": SYSTEM_PROMPT_FIRST_SUMMARY},
                      {"role": "user", "content": message}],
            temperature=1
        )
        summary = remove_reasoning_from_output(summary)
        summary = clean_json_tags(summary)
        summary = json.loads(summary)

        STATE.paragraphs[j].research.latest_summary = summary["paragraph_latest_state"]

        pprint(STATE)

        # Reflection Summary per paragraph

        input_schema_reflection_summary = {
            "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "search_query": {"type": "string"},
                        "search_results": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "paragraph_latest_state": {"type": "string"}
                    }
        }

        output_schema_reflection_summary = {
            "type": "object",
                    "properties": {
                        "updated_paragraph_latest_state": {"type": "string"}
                    }
        }

        SYSTEM_PROMPT_REFLECTION_SUMMARY = f"""
            You are a Deep Research assistan.
            You will be given a search query, search results, paragraph title and expected content for the paragraph in a report that you are researching.
            You are iterating on the paragraph and the latest state of the paragraph is also provided.
            The data will be in the following json schema definition:

            <INPUT JSON SCHEMA>
            {json.dumps(input_schema_reflection_summary, indent=2)}
            </INPUT JSON SCHEMA>

            Your job is to enrich the current latest state of the paragraph with the search results considering expected content.
            Do not remove key information from the latest state and try to enrich it, only add information that is missing.
            Structure the paragraph properly to be included in the report.
            Format the output in json with the following json schema definition:

            <OUTPUT JSON SCHEMA>
            {json.dumps(output_schema_reflection_summary, indent=2)}
            </OUTPUT JSON SCHEMA>

            Make sure that the output is a json object with an output json schema defined above.
            Only return the json object, no explanation or additional text.
            """

        for i in range(NUM_REFLECTIONS):
            print(f"Running reflection: {i+1}")
            pprint("Waiting Reflections for 5 seconds...")
            time.sleep(5)  # Pause execution for 5 seconds
            pprint("Now running Reflections!")

            message = {"paragraph_latest_state": paragraph.research.latest_summary,
                       "title": paragraph.title,
                       "content": paragraph.content}

            message = json.dumps(message)
            summary = client.chat.completions.create(
                model=LLM,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_REFLECTION_SUMMARY},
                          {"role": "user", "content": message}],
                temperature=1
            )
            summary = remove_reasoning_from_output(summary)
            summary = clean_json_tags(summary)
            summary = json.loads(summary)

            search_results = tavily_search(summary["search_query"])

            _ = update_state_with_search_results(search_results, j, STATE)

            pprint("Waiting Reflections mutations for 5 seconds...")
            time.sleep(5)  # Pause execution for 5 seconds
            pprint("Now running Reflections mutations!")

            message = {
                "title": paragraph.title,
                "content": paragraph.content,
                "search_query": search_results["query"],
                "search_results": [result["raw_content"][0:20000] for result in search_results["results"] if result["raw_content"]],
                "paragraph_latest_state": paragraph.research.latest_summary
            }

            message = json.dumps(message)

            summary = client.chat.completions.create(
                model=LLM,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_REFLECTION_SUMMARY},
                          {"role": "user", "content": message}],
                temperature=1
            )
            summary = remove_reasoning_from_output(summary)
            summary = clean_json_tags(summary)
            summary = json.loads(summary)

            STATE.paragraphs[j].research.latest_summary = summary["updated_paragraph_latest_state"]
    report_data = [{"title": paragraph.title, "paragraph_latest_state":
                    paragraph.research.latest_summary} for paragraph in STATE.paragraphs]

    # Report Formatting

    pprint("Waiting Report Formatting  for 5 seconds...")
    time.sleep(5)  # Pause execution for 5 seconds
    pprint("Now running Report Formatting!")

    input_schema_report_formatting = {
        "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "paragraph_latest_state": {"type": "string"}
                    }
                }
    }

    SYSTEM_PROMPT_REPORT_FORMATTING = f"""
        You are a Deep Research assistan. You have already performed the research and construted final versions of all paragraphs in the report.
        You will get the data in the following json format:

        <INPUT JSON SCHEMA>
        {json.dumps(input_schema_report_formatting, indent=2)}
        </INPUT JSON SCHEMA>

        Your job is to format the Report nicely and return it in MarkDown.
        If Conclusion paragraph is not present, add it to the end of the report from the latest state of the other paragraphs.
        Use titles of the paragraphs to create a title for the report.
        """

    message = json.dumps(report_data)

    summary = client.chat.completions.create(
        model=LLM,
        messages=[{"role": "system", "content": SYSTEM_PROMPT_REFLECTION_SUMMARY},
                  {"role": "user", "content": message}],
        temperature=1
    )
    summary = remove_reasoning_from_output(summary)
    summary = clean_json_tags(summary)
    final_report = json.loads(summary)

    pprint(final_report)

    with open(f"reports/report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md", "w") as f:
        f.write(final_report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, default=QUERY)
    args = parser.parse_args()

    main(args.topic)

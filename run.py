from ai.providers import get_model
from deep_research import deep_research, write_final_answer, write_final_report, ResearchResult
from feedback import generate_feedback
import asyncio
import aiofiles

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
console = Console()
import re

def strip_rich_markup(text):
    # Remove [style]...[/style] tags for input prompts
    return re.sub(r'\[.*?\](.*?)\[/.*?\]', r'\1', text)

model = get_model()

# Helper function for consistent logging
def log(*args):
    """Prints messages to the console."""
    print(*args)

# Helper function to ask questions asynchronously
async def ask_question(prompt: str) -> str:
    if console:
        # Show prompt in bold blue, but input() must be plain
        console.print(Text(strip_rich_markup(prompt), style="bold blue"))
        return await asyncio.to_thread(input, "Your answer: ")
    else:
        return await asyncio.to_thread(input, prompt)


async def run():
    if console:
        console.print(Panel.fit(Text(f"Using model: {model}", style="bold cyan"), border_style="cyan"))
    else:
        print(f"Using model: {model}")
    initial_query = await ask_question("What would you like to research?")
    if console:
        console.print(Panel.fit(Text(f"Initial query: {initial_query}", style="bold magenta bold"), border_style="magenta"))
    else:
        print(f"Initial query: {initial_query}")
    try:
        breadth = int(await ask_question("Enter research breadth (recommended 2-10, default 4): ") or 4)
        if console:
            console.print(Text(f"Research breadth set to: {breadth}", style="bold green"))
        else:
            print(f"Research breadth set to: {breadth}")
    except ValueError:
        breadth = 4
    try:
        depth = int(await ask_question("Enter research depth (recommended 1-5, default 2): ") or 2)
        if console:
            console.print(Text(f"Research depth set to: {depth}", style="bold green"))
        else:
            print(f"Research depth set to: {depth}")
    except ValueError:
        depth = 2
    report_type = await ask_question(
        "Do you want to generate a long report or a specific answer? ( 1 for report 2 for answer, default 1): "
    )
    is_report = report_type.strip().lower() != "2"
    combined_query = initial_query
    if is_report:
        if console:
            console.print(Panel.fit(Text("Creating research plan...", style="bold cyan"), border_style="cyan"))
        else:
            print("Creating research plan...")
        follow_up_questions = await generate_feedback(query= initial_query)
        if console:
            console.print(Text("\nTo better understand your research needs, please answer these follow-up questions:", style="bold yellow"))
        else:
            print("\nTo better understand your research needs, please answer these follow-up questions:")
        answers = []
        for question in follow_up_questions:
            answer = await ask_question(question)
            answers.append(answer)
        qa_block = "\n".join([f"Q: {q}\nA: {a}" for q, a in zip(follow_up_questions, answers)])
        combined_query = f"Initial Query: {initial_query}\nFollow-up Questions and Answers:\n{qa_block}"
    if console:
        console.print(Panel.fit(Text("Starting research...", style="bold green"), border_style="green"))
    else:
        print("\nStarting research...\n")
    research_results: ResearchResult = await deep_research(
        query= combined_query,
        breadth= breadth,
        depth= depth)
    learnings = research_results.learnings
    visited_urls = research_results.visitedUrls

    if console:
        console.print(Panel.fit(Text("Learnings:", style="bold cyan"), border_style="cyan"))
        for l in learnings:
            console.print(Text(f"- {l}", style="bold green"))
        console.print(Panel.fit(Text(f"Visited URLs ({len(visited_urls)}):", style="bold magenta"), border_style="magenta"))
        for u in visited_urls:
            console.print(Text(f"- {u}", style="bold yellow"))
    else:
        print("\n\nLearnings:\n\n" + "\n".join(learnings))
        print(f"\n\nVisited URLs ({len(visited_urls)}):\n\n" + "\n".join(visited_urls))
    if console:
        console.print(Panel.fit(Text("Writing final report...", style="bold green"), border_style="green"))
    else:
        print("Writing final report...")
    if is_report:
        report = await write_final_report(
            prompt= combined_query,
            learnings= learnings,
            visited_urls= visited_urls
        )
        async with aiofiles.open("report.md", "w", encoding="utf-8") as f:
            await f.write(report)
        if console:
            console.print(Panel.fit(Text("Final Report:", style="bold cyan"), border_style="cyan"))
            console.print(Markdown(report), style="bold")
            console.print(Text("\nReport has been saved to report.md", style="bold green"))
        else:
            print("\n\nFinal Report:\n\n" + report)
            print("\nReport has been saved to report.md")
    else:
        answer = await write_final_answer(
            prompt= combined_query,
            learnings= learnings
        )
        async with aiofiles.open("answer.md", "w", encoding="utf-8") as f:
            await f.write(answer)
        if console:
            console.print(Panel.fit(Text("Final Answer:", style="bold cyan"), border_style="cyan"))
            console.print(Markdown(answer), style="bold")
            console.print(Text("\nAnswer has been saved to answer.md", style="bold green"))
        else:
            print("\n\nFinal Answer:\n\n" + answer)
            print("\nAnswer has been saved to answer.md")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log("\nProcess interrupted by user. Exiting.")
    except Exception as e:
        log(f"\nAn unexpected error occurred: {e}")

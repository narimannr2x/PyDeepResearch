from firecrawl import AsyncFirecrawlApp, ScrapeOptions
from ai.providers import generate_structured_response_async, get_model, trim_prompt
from prompts import system_prompt_func
from pydantic import BaseModel, Field
from typing import List, Optional,Callable,  Any, Dict
import math

from dotenv import load_dotenv
import asyncio
import os 
from dataclasses import dataclass



from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
console = Console()
import re
def strip_rich_markup(text):
    return re.sub(r'\[.*?\](.*?)\[/.*?\]', r'\1', text)




load_dotenv()
#######################################################################
ConcurrencyLimit = int(os.getenv("FIRECRAWL_CONCURRENCY", "1"))
semaphore = asyncio.Semaphore(ConcurrencyLimit)

model = get_model()
firecrawl = AsyncFirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY", ""))
system_prompt = system_prompt_func()
#######################################################################
class QueryItem(BaseModel):
    query: str = Field(..., description="The SERP query")
    researchGoal: str = Field(
        ..., 
        description=(
            "First talk about the goal of the research that this query is meant to accomplish, "
            "then go deeper into how to advance the research once the results are found, "
            "mention additional research directions. Be as specific as possible, especially for additional research directions."
        )
    )


class SerpSchema(BaseModel):
    queries: List[QueryItem] = Field(..., description="List of SERP queries, max of {numQueries}")
###################################################################################
class FollowUpSchema(BaseModel):
    learnings: List[str] = Field(
        ..., 
        description="List of learnings, max of {numLearnings}"
    )
    followUpQuestions: List[str] = Field(
        ..., 
        description="List of follow-up questions to research the topic further, max of {numFollowUpQuestions}"
    )
####################################################################################

class FinalReportSchema(BaseModel):
    reportMarkdown: str = Field(..., description="Final report on the topic in Markdown")

###########################################################################################
class FinalAnswerSchema(BaseModel):
    exactAnswer: str = Field(
        ..., 
        description="The final answer, make it short and concise, just the answer, no other text"
    )

###########################################################################################
@dataclass
class ResearchProgress:
    currentDepth: int
    totalDepth: int
    currentBreadth: int
    totalBreadth: int
    totalQueries: int
    completedQueries: int
    currentQuery: Optional[str] = None
@dataclass
class ResearchResult:
    learnings: List[str]
    visitedUrls: List[str]
###################################################################################################
async def generate_serp_queries(query: str, num_queries: int = 3, learnings: list[str] | None = None):
    user_content = (
        f"Given the following prompt from the user, generate a list of SERP queries to "
        f"research the topic. Return a maximum of {num_queries} queries, but feel free "
        f"to return fewer if the prompt is already clear. Make each query unique: \n\n"
        f"<prompt>{query}</prompt>\n\n"
    )
    
    if learnings:
        user_content += (
            "Here are some learnings from previous research; use them to generate more "
            "specific queries:\n" + "\n".join(f"- {l}" for l in learnings)
        )
    if console:
        console.print(Panel.fit(Text("Generating SERP queries...", style="bold cyan"), border_style="cyan"))
        console.print(Text(f"Prompt: {query}", style="bold"))
    else:
        print("user_content:", user_content)
    response = await generate_structured_response_async(
        prompt=user_content,
        system_prompt=system_prompt,
        model=model,
        format_schema=SerpSchema,
    )
    if console:
        console.print(Text("SERP queries generated!", style="bold green"))
    else:
        print("generated")
    response_parsed = response.output_parsed
    return response_parsed.queries[:num_queries]  # type: ignore


async def process_serp_result(query,result,num_learnings= 3 , num_follow_up_questions = 3):
    contents = [
        trim_prompt(item["markdown"], 25000)
        for item in result.get("data", [])
        if item.get("markdown")
    ]

    if console:
        console.print(Panel.fit(Text(f"Ran: {query} | {len(contents)} contents found", style="bold magenta"), border_style="magenta"))
    else:
        print(f"Ran {query}, found {len(contents)} contents")
    # Prepare prompt
    content_block = "\n".join(f"<content>\n{c}\n</content>" for c in contents)
    prompt = trim_prompt(
        f"""Given the following contents from a SERP search for the query <query>{query}</query>, generate a list of learnings from the contents. \
Return a maximum of {num_learnings} learnings, but feel free to return less if the contents are clear. \
Make sure each learning is unique and not similar to each other. The learnings should be concise and to the point, \
as detailed and information dense as possible. Make sure to include any entities like people, places, companies, \
products, things, etc in the learnings, as well as any exact metrics, numbers, or dates. \
The learnings will be used to research the topic further.

<contents>{content_block}</contents>"""
    )
    response = await generate_structured_response_async(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        format_schema=FollowUpSchema,
    )
    return response.output_parsed


async def write_final_report(prompt: str, learnings: list[str], visited_urls: list[str]
                             ):
    learnings_string = "\n".join(f"<learning>\n{learning}\n</learning>" for learning in learnings)
    full_prompt = trim_prompt(
        f"""Given the following prompt from the user, write a final report on the topic using the learnings from research. 
Make it as detailed as possible, aim for 3 or more pages, include ALL the learnings from research:

<prompt>{prompt}</prompt>

Here are all the learnings from previous research:

<learnings>
{learnings_string}
</learnings>"""
    )
    response = await generate_structured_response_async(
        prompt=full_prompt,
        system_prompt=system_prompt,
        model=model,
        format_schema=FinalReportSchema,
    )
    response_parsed = response.output_parsed.reportMarkdown # type: ignore
    urls_section = "\n\n## Sources\n\n" + "\n".join(f"- {url}" for url in visited_urls)
    return response_parsed + urls_section  # type: ignore


async def write_final_answer(prompt: str, learnings: list[str]):
    learnings_string = "\n".join(f"<learning>\n{learning}\n</learning>" for learning in learnings)
    full_prompt = trim_prompt(
        f"""Given the following prompt from the user, write a final answer on the topic using the learnings from research. 
Follow the format specified in the prompt. Do not yap or babble or include any other text than the answer besides the format specified in the prompt. 
Keep the answer as concise as possible - usually it should be just a few words or maximum a sentence. 
Try to follow the format specified in the prompt (for example, if the prompt is using Latex, the answer should be in Latex. 
If the prompt gives multiple answer choices, the answer should be one of the choices).

<prompt>{prompt}</prompt>

Here are all the learnings from research on the topic that you can use to help answer the prompt:

<learnings>
{learnings_string}
</learnings>"""
    )
    response = await generate_structured_response_async(
        prompt=full_prompt,
        system_prompt=system_prompt,
        model=model,
        format_schema=FinalAnswerSchema,
    )
    response_parsed = response.output_parsed.exactAnswer  # type: ignore
    return response_parsed  # type: ignore

def report_progress(
    update: Dict[str, Any], 
    progress: 'ResearchProgress', 
    on_progress: Optional[Callable[['ResearchProgress'], None]] = None
):
    for key, value in update.items():
        setattr(progress, key, value)
    if on_progress:
        on_progress(progress)


async def deep_research(query: str,breadth:int, depth:int,learnings: Optional[List[str]] = None,
    visited_urls: Optional[List[str]] = None,on_progress:  Optional[Callable[[ResearchProgress], None]] = None):
    learnings = learnings or []
    visited_urls = visited_urls or []
    progress = ResearchProgress(
        currentDepth=depth,
        totalDepth=depth,
        currentBreadth=breadth,
        totalBreadth=breadth,
        totalQueries=0,
        completedQueries=0,
    )
    if console:
        console.print(Panel.fit(Text(f"Generating SERP queries for: {query}", style="bold cyan"), border_style="cyan"))
    else:
        print("generating SERP queries...")
    serp_queries = await generate_serp_queries(
    query=query,
    learnings=learnings,
    num_queries=breadth
)
    
    if not serp_queries:
        if console:
            console.print(Text("No SERP queries generated, returning current state", style="bold red"))
        else:
            print("No SERP queries generated, returning current state")
        return ResearchResult(learnings=learnings, visitedUrls=visited_urls)
    
    report_progress(
    {
        "totalQueries": len(serp_queries),
        "currentQuery": serp_queries[0].query if serp_queries else None,
    },
    progress=progress,
    on_progress=on_progress
)   
    async def limited_deep_query(
        serp_query,
        semaphore,
        breadth,
        depth,
        learnings,
        visited_urls,
        progress,
        on_progress):
        try:
            # Initialize variables that might be used outside semaphore context
            new_breadth = math.ceil(breadth / 2)
            new_depth = depth - 1
            next_query = ""
            all_learnings = learnings
            all_urls = visited_urls
            
            async with semaphore:
                if console:
                    console.print(Panel.fit(Text(f"Searching with Firecrawl: {serp_query.query}", style="bold blue"), border_style="blue"))
                else:
                    print(f"searching with firecrawl for: {serp_query.query}")
                result = await firecrawl.search(
                    query=serp_query.query,
                    limit=5,
                    scrape_options=ScrapeOptions(formats=["markdown"]),
                    timeout=15000
                )
                new_urls = [item['url'] for item in result["data"] if item.get('url')] # type: ignore
                
                if console:
                    console.print(Text("Processing SERP result...", style="bold green"))
                else:
                    print("processing SERP result")
                new_learnings = await process_serp_result(
                    query=serp_query.query,
                    result=result,
                    num_follow_up_questions=new_breadth,
                )
                all_learnings = learnings + new_learnings.learnings # type: ignore
                all_urls = visited_urls + new_urls
                
                # Prepare data for potential recursive call
                if new_depth > 0:
                    if console:
                        console.print(Text(f"Researching deeper... Breadth: {new_breadth} Depth: {new_depth}", style="bold yellow"))
                    else:
                        print(f"Researching deeper, breadth: {new_breadth}, depth: {new_depth}")
                    report_progress(
                        {
                            "currentDepth": new_depth,
                            "currentBreadth": new_breadth,
                            "completedQueries": progress.completedQueries + 1,
                            "currentQuery": serp_query.query,
                        },
                        progress=progress,
                        on_progress=on_progress
                    )
                    next_query = (
                        f"Previous research goal: {serp_query.researchGoal}\n"
                        f"Follow-up research directions: {', '.join(new_learnings.followUpQuestions)}" # type: ignore
                    ).strip()
                    if console:
                        console.print(Panel.fit(Text(f"Next query: {next_query}", style="bold magenta"), border_style="magenta"))
                    else:
                        print(f"Next query: {next_query}")
            
            # Make recursive call outside of semaphore context
            if new_depth > 0:
                return await deep_research(
                    query=next_query,
                    breadth=new_breadth,
                    depth=new_depth,
                    learnings=all_learnings,
                    visited_urls=all_urls,
                    on_progress=on_progress,
                )
            else:
                report_progress(
                    {
                        "currentDepth": 0,
                        "completedQueries": progress.completedQueries + 1,
                        "currentQuery": serp_query.query,
                    },
                    progress=progress,
                    on_progress=on_progress
                )
                return ResearchResult(learnings=all_learnings, visitedUrls=all_urls)
        
        except Exception as e:
            if "Timeout" in str(e):
                if console:
                    console.print(Text(f"Timeout error running query: {serp_query.query}: {e}", style="bold red"))
                else:
                    print(f"Timeout error running query: {serp_query.query}: {e}")
            else:
                if console:
                    console.print(Text(f"Error running query: {serp_query.query}: {e}", style="bold red"))
                else:
                    print(f"Error running query: {serp_query.query}: {e}")
            return ResearchResult(learnings=learnings, visitedUrls=visited_urls)
    
    tasks = [
        limited_deep_query(
            serp_query,
            semaphore,
            breadth=breadth,
            depth=depth,
            learnings=learnings,
            visited_urls=visited_urls,
            progress=progress,
            on_progress=on_progress
        )
        for serp_query in serp_queries
    ]
    results = await asyncio.gather(*tasks)
    return ResearchResult(
        learnings=list(set(l for r in results for l in r.learnings)),
        visitedUrls=list(set(u for r in results for u in r.visitedUrls))
    )
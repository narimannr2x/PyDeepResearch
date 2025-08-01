# PyDeepResearch

**PyDeepResearch** is a minimal, Python-based implementation of [deep-research](https://github.com/dzhng/deep-research), an excellent TypeScript project. It generates search queries, scrapes and summarizes web results, and produces detailed Markdown reports or concise answers—all from a simple command-line interface.

## Features

- Automated query generation based on user query
- web searching and scraping using Firecrawl
- Recursive research with customizable breadth and depth
- Summarizes findings and generates Markdown reports or concise answers
- Interactive CLI interface for user input and follow-up questions
- Saves output to `report.md` (detailed) or `answer.md` (concise)
- Source URLs included in reports

## Demo

![demo1](.github/visuals/pydeepresearch.gif)

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/narimannr2x/PyDeepResearch.git
   cd deepresearch
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**

   - Copy `.env.example` to `.env` and fill in the required API keys.
   - **Note:** Firecrawl has a concurrency limit of 2 and also enforces a rate limit on requests per minute. If you set `FIRECRAWL_CONCURRENCY` to 2 or higher and do not have a Pro account, you may encounter rate limiting issues.
   - Example:

   ```txt
    FIRECRAWL_API_KEY=your_firecrawl_api_key
    FIRECRAWL_CONCURRENCY=2
    # Add other keys as needed
   ```

## Usage

Run the assistant from the command line:

```bash
python run.py
```

You will be prompted to enter:

1. The research topic or question
2. Research breadth (number of queries per level)
3. Research depth (levels of recursion)
4. Report type: detailed report or concise answer

You may also be asked follow-up questions for more context.

**Output:**

- A detailed Markdown report (`report.md`) or a concise answer (`answer.md`) will be generated in the project directory.

## Configuration

- **API Keys:** Required for Firecrawl and OpenAi. Set these in your `.env` file.
- **Concurrency:** Adjust `FIRECRAWL_CONCURRENCY` in `.env` to control parallel scraping.
- **Model:** LLM provider/model can be configured in the code.

## Output

- `report.md`: Detailed Markdown report with all findings and source URLs.
- `answer.md`: Concise answer to the research question.

## License

This project is licensed under the MIT License.

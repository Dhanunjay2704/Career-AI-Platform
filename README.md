# Career AI Platform

A comprehensive AI-powered platform built with Gradio and LangChain to assist with various career-related tasks. This application features 6 specialized AI agents that provide insights, recommendations, and resources for career development.

## 🚀 Features

### 6 AI Agents

1. **🎯 Skill to Career Mapper**
   - Analyze industry demand for specific skills
   - Find matching job openings
   - Custom query support

2. **🎤 Interview Prep Agent**
   - Generate 20 interview questions for any role
   - Provide preparation tips and strategies
   - Recommend YouTube videos, blogs, and courses

3. **💰 Salary Insights Agent**
   - Get salary ranges by experience level
   - Identify top paying companies
   - Compare salaries across cities

4. **📚 Course Finder Agent**
   - Find free courses on Coursera, YouTube, edX
   - Discover paid certifications from Google, Microsoft, AWS
   - Get step-by-step learning roadmaps
   - Compare best learning platforms

5. **🚀 Startup Jobs Agent**
   - Discover top funded startups in any domain
   - Find live job openings in startups
   - Analyze hiring trends and in-demand roles

6. **⚔️ Skill Comparison Agent**
   - Compare two skills side-by-side
   - Analyze job demand, salary, learning curve, future scope
   - Get live job counts and samples

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8+
- API Keys for:
  - Google Gemini (GEMINI_API_KEY)
  - Tavily Search (TAVILY_API_KEY)
  - RapidAPI JSearch (RAPID_API_KEY)
  - Google Serper (SERPER_API_KEY)

### Installation

1. Clone or download the project files
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   TAVILY_API_KEY=your_tavily_api_key
   RAPID_API_KEY=your_rapidapi_key
   SERPER_API_KEY=your_serper_api_key
   ```

### Running the Application

```bash
python app.py
```

The application will start a local web server. Open the provided URL in your browser to access the platform.

## 📖 Usage

1. **Launch the app** using the command above
2. **Navigate through tabs** for different AI agents
3. **Fill in the required fields** for each agent
4. **Click the action button** to get AI-generated insights
5. **View results** in the formatted output area

### Example Usage

- **Skill Mapper**: Enter "Python" as skill and "Bangalore" as location
- **Interview Prep**: Select "Data Analyst" role, "Fresher" level, "Technical" round
- **Salary Insights**: Enter "Full Stack Developer" and select "India"
- **Course Finder**: Enter "Machine Learning" and select "Beginner" level
- **Startup Jobs**: Enter "FinTech" domain, "Fresher" experience, "Bangalore" location
- **Skill Compare**: Compare "React" vs "Angular" for "Get a Job" goal

## 🏗️ Architecture

- **Frontend**: Gradio (web UI)
- **Backend**: Python with LangChain agents
- **LLM**: Google Gemini 2.5 Flash
- **Search Tools**: Tavily, Google Serper, RapidAPI JSearch
- **Styling**: Custom CSS with Soft theme

## 🤝 Contributing

Feel free to contribute by:
- Reporting bugs
- Suggesting new features
- Improving documentation
- Adding more AI agents

## 📄 License

This project is open-source. Please check the license file for details.

## ⚠️ Disclaimer

This tool provides AI-generated insights and recommendations. Always verify information from multiple sources and use professional judgment for career decisions.</content>
<parameter name="filePath">c:\Users\DHANUNJAY\BUILDING LLM APPLICATIONS\AI Agents\career-ai-platform\README.md
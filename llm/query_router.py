from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]

llm = ChatOllama(model=model_name, format="json", temperature=0)

system_prompt = """You are an expert at routing a user question to a vector database, project database, or general knowledge.\n
    You operate in a metrics monitoring tool designed for use in a software engineering project course.\n
    Use the vector database for questions related to meta-information about the software engineering project course, such as deadlines for submissions.\n
    Use the project database for questions related to the user's project, such as how is the project doing or what could be improved.\n
    The project database only has information on the project's working hours, project members' working hours, project metrics, and project risks.\n
    You do not need to be stringent with the keywords in the question related to these topics.\n
    Otherwise, use general knowledge.\n
    Give a binary option 'vector_database', 'project_database', or 'general_knowledge' based on the question.\n
    Return the option as JSON with a single key 'datasource' and no preamble or explanation."""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{question}"),
])

chain = prompt_template | llm | JsonOutputParser()


def route_question(question: str) -> str:
    result = chain.invoke({"question": question})
    print(result.get("datasource"))
    return result.get("datasource")

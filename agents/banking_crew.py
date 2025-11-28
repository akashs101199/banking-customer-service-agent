"""
Banking Crew
Defines the CrewAI agents and tasks for the banking system
"""
import os
from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models import ChatOllama
from langchain.tools import Tool

from agents.tools import BankingTools
from config import settings

# Initialize Open Source LLM (Ollama)
llm = ChatOllama(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.7
)

class BankingCrew:
    """Orchestrates the banking crew"""

    def __init__(self):
        self.tools = BankingTools()

    def run(self, query: str, customer_context: dict):
        """
        Run the crew to process a user query
        """
        # Define Agents
        senior_banker = Agent(
            role='Senior Banker',
            goal='Oversee customer service and handle general account inquiries',
            backstory='You are an experienced banker who ensures customers get the best service. You delegate complex tasks to specialists.',
            verbose=True,
            allow_delegation=True,
            llm=llm,
            tools=[self.tools.create_account, self.tools.get_account_details]
        )

        transaction_specialist = Agent(
            role='Transaction Specialist',
            goal='Handle all payments, transfers, and bill pays accurately',
            backstory='You are a precise specialist who manages funds. You ensure every penny is accounted for.',
            verbose=True,
            allow_delegation=False,
            llm=llm,
            tools=[self.tools.transfer_funds, self.tools.pay_bill]
        )

        investment_advisor = Agent(
            role='Investment Advisor',
            goal='Manage customer portfolios and execute trades',
            backstory='You are a savvy market expert who helps customers grow their wealth.',
            verbose=True,
            allow_delegation=False,
            llm=llm,
            tools=[self.tools.get_portfolio, self.tools.trade_stocks]
        )

        loan_officer = Agent(
            role='Loan Officer',
            goal='Evaluate loan applications and provide credit decisions',
            backstory='You are a risk assessment expert who helps customers get financing responsibly.',
            verbose=True,
            allow_delegation=False,
            llm=llm,
            tools=[self.tools.apply_for_loan]
        )

        # Define Task
        # We create a single dynamic task based on the user query
        # In a more complex setup, we might have a router agent create specific tasks
        
        context_str = f"Customer Context: {customer_context}"
        
        main_task = Task(
            description=f"Process the following customer query: '{query}'.\n{context_str}\n"
                        f"Identify the customer's intent and use the appropriate tools to fulfill their request. "
                        f"If you need to perform actions like transfers or trading, delegate to the specialist. "
                        f"Provide a helpful and professional response to the customer.",
            agent=senior_banker,
            expected_output="A helpful response to the customer confirming the action taken or providing the requested information."
        )

        # Create Crew
        crew = Crew(
            agents=[senior_banker, transaction_specialist, investment_advisor, loan_officer],
            tasks=[main_task],
            verbose=2,
            process=Process.sequential
        )

        result = crew.kickoff()
        return result

# Global instance
banking_crew = BankingCrew()

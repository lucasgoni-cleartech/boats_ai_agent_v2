"""
Main application for the Conversational Looker Agent.

MVP implementation with simple CLI interface for testing.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.modules.agent.conversational_agent import ConversationalAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversationalAgentCLI:
    """Simple CLI interface for the conversational agent."""
    
    def __init__(self, config_path: str):
        """Initialize the CLI with agent configuration."""
        self.agent = ConversationalAgent(config_path)
        self.session_id = "cli_session_001"
        
    async def initialize(self):
        """Initialize the agent (async setup)."""
        await self.agent.initialize_looker_schema()
        logger.info("Agent initialized successfully")
        
    async def run_interactive(self):
        """Run interactive CLI session."""
        print("\n🐧 Conversational Looker Agent - MVP")
        print("=" * 50)
        print("Ask me questions about your data!")
        print("Type 'help' for capabilities, 'quit' to exit")
        print("=" * 50)
        
        # Show session info
        session_info = self.agent.get_session_info()
        print(f"\nStatus: {session_info['agent_status']}")
        print(f"Looker Connected: {session_info['looker_connected']}")
        print(f"Available Recipes: {session_info['available_recipes']}")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n🔍 Your question: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye! 👋")
                    break
                    
                if user_input.lower() in ['help', 'h']:
                    self._show_help()
                    continue
                    
                if user_input.lower() == 'status':
                    self._show_status()
                    continue
                    
                if user_input.lower() == 'clear':
                    response = await self.agent.process_query("clear history", self.session_id)
                    print(f"\n🤖 {response['message']}")
                    continue
                
                if not user_input:
                    continue
                
                # Process the query
                print("\n🤔 Processing your question...")
                response = await self.agent.process_query(user_input, self.session_id)
                
                # Display response
                print(f"\n🤖 {response['message']}")
                
                # Show additional info if available
                if response.get('status') == 'success' and response.get('data'):
                    data = response['data']
                    if data and len(data) > 0:
                        print(f"\n📊 Retrieved {len(data)} rows of data")
                        
                        # Show first few rows as preview
                        if len(data) <= 3:
                            print("Sample data:")
                            for i, row in enumerate(data, 1):
                                print(f"  {i}. {row}")
                        else:
                            print("Sample data (first 3 rows):")
                            for i, row in enumerate(data[:3], 1):
                                print(f"  {i}. {row}")
                
                if response.get('status') == 'error':
                    print(f"❌ Error: {response.get('error', 'Unknown error')}")
                    
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.error(f"CLI error: {e}")
    
    def _show_help(self):
        """Show help information."""
        print("\n📚 Help - Conversational Looker Agent")
        print("=" * 50)
        print("Sample questions you can ask:")
        print("• 'Show me revenue by country'")
        print("• 'What are the trends over time?'")
        print("• 'Top 10 products by revenue'") 
        print("• 'How are customers segmented?'")
        print("• 'Give me an executive summary'")
        print("\nCommands:")
        print("• 'help' - Show this help")
        print("• 'status' - Show agent status")
        print("• 'clear' - Clear conversation history")
        print("• 'quit' - Exit the application")
        print("=" * 50)
    
    def _show_status(self):
        """Show current agent status."""
        session_info = self.agent.get_session_info()
        memory_stats = session_info['memory_stats']
        
        print("\n📊 Agent Status")
        print("=" * 30)
        print(f"Agent: {session_info['agent_status']}")
        print(f"Looker Connected: {session_info['looker_connected']}")
        print(f"Available Recipes: {session_info['available_recipes']}")
        print(f"Conversation Turns: {memory_stats['total_turns']}")
        print(f"Data Interests: {memory_stats['data_interests_count']}")
        print("=" * 30)


async def main():
    """Main application entry point."""
    try:
        # Verify OpenAI API key is loaded
        import os
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("❌ OPENAI_API_KEY not found in environment variables")
            print("Make sure you have a .env file with your OpenAI API key")
            sys.exit(1)
        
        print(f"✅ OpenAI API key loaded: {openai_key[:10]}...{openai_key[-4:]}")
        
        # Get config path
        config_path = Path(__file__).parent / "config" / "agent_config.yaml"
        
        if not config_path.exists():
            print(f"❌ Configuration file not found: {config_path}")
            sys.exit(1)
        
        # Initialize and run CLI
        cli = ConversationalAgentCLI(str(config_path))
        await cli.initialize()
        await cli.run_interactive()
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
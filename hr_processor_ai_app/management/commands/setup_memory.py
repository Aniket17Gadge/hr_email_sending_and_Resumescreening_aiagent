from django.core.management.base import BaseCommand
from hr_processor_ai_app.memory_manager import memory_manager
import asyncio

class Command(BaseCommand):
    help = 'Setup LangGraph PostgreSQL memory tables'

    def handle(self, *args, **options):
        async def setup():
            success = await memory_manager.initialize()
            if success:
                self.stdout.write(
                    self.style.SUCCESS('✅ LangGraph memory tables setup complete')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Failed to setup memory tables')
                )
        
        asyncio.run(setup())

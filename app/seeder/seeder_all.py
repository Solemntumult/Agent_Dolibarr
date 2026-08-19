from seeder.agent_settings.agent_settings_seeder import AgentSettingsSeeder
from seeder.super_admin.super_admin_seeder import SuperAdminSeeder


class SeederAll:
    @staticmethod
    def run_all():
        SuperAdminSeeder.run()
        AgentSettingsSeeder.run()

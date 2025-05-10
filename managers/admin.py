from django.contrib import admin
from .models import *


admin.site.register(Manager)


admin.site.register(EmergencyContactManager)
admin.site.register(AddressManager)
admin.site.register(BackgroundManager)
admin.site.register(BenefitsManager)
admin.site.register(SkillManager)
admin.site.register(IdentificationManager)
admin.site.register(WorkScheduleManager)


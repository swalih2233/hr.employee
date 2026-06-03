import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr.settings') # Need to find the settings file
django.setup()
from users.models import User
from employe.models import Employe
from managers.models import Manager
try:
    u = User.objects.get(email='swalihkpx@gmail.com')
    e = Employe.objects.filter(user=u).first()
    m = Manager.objects.filter(user=u).first()
    print(f'E: {e.image if e else "None"}')
    print(f'M: {m.image if m else "None"}')
except Exception as err:
    print(err)

from django.template import Context, loader
from django.shortcuts import render_to_response
from packageporter.oper import UpdateFromKoji

def home(request):
    ufk = UpdateFromKoji()
    ufk.update_repos()
    ufk.update_owners()
    ufk.update_packages()
    ufk.update_builds()
    return render_to_response('index.html')

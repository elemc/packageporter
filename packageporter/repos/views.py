from django.template import Context, loader
from django.shortcuts import render_to_response
from django.http import Http404, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_protect
from django import forms

from packageporter.repos.models import Repos, RepoTypes

class NewRepoForm(forms.Form):
    name = forms.CharField()

@csrf_protect
@login_required(login_url='/accounts/login/')
def index(request):
    if request.method == 'POST':
        form = NewRepoForm(request.POST)
        if form.is_valid():
            r_name = form.cleaned_data['name']
            if "add_new_repo_submit" in request.POST:
                try:
                    newrepo = Repos(repo_name=r_name)
                except:
                    raise Http404
                newrepo.save()
            elif "add_new_repotype_submit" in request.POST:
                try:
                    newrt = RepoTypes(rt_name=r_name)
                except:
                    raise Http404
                newrt.save()
                
            return HttpResponseRedirect('/repos/')
    
    try:
        repos = Repos.objects.order_by('repo_name')
        rt = RepoTypes.objects.order_by('rt_name')
    except:
        raise Http404

    if request.user.has_perm('packageporter.add_repos'):
        form = NewRepoForm()
    else:
        form = None

    toform = { 'can_add': request.user.has_perm('packageporter.add_repos'),
               'repos': repos,
               'repotypes': rt,
               'form': form }
    toform.update(csrf(request))
    return render_to_response('repos/index.html', toform)


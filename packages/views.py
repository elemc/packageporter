from django.template import Context, loader
from django.shortcuts import render_to_response
from packageporter.packages.models import BuildedPackages
from packageporter.repos.models import RepoTypes
from django.http import Http404, HttpResponseRedirect

from django import forms

from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_protect

from django.forms.formsets import formset_factory

from packageporter.oper import PushPackagesToRepo

def get_packages():
    try:
        bpkg_list = BuildedPackages.objects.filter(pushed=False).order_by('completion_time')
    except:
        return []
    return bpkg_list

def get_all_repo_types():
    try:
        r = RepoTypes.objects.all()
    except:
        return []
    
    res = []
    for t in r:
        if (t.rt_id is not None) and (t.rt_name is not None):
            res.append( (t.rt_id, t.rt_name) )
    return res


class SelectPackagesToPush(forms.Form):
    selected_package    = forms.BooleanField(required=False)
    package_name        = forms.CharField(widget=forms.HiddenInput)
    completion_time     = forms.DateTimeField(widget=forms.HiddenInput)
    repo_type           = forms.ChoiceField(choices=get_all_repo_types())
    pkg_id              = forms.IntegerField(widget=forms.HiddenInput)
    build_id            = forms.IntegerField(widget=forms.HiddenInput)
SelectPackagesFormSet = formset_factory(SelectPackagesToPush, extra=0)

def initial_data():
    bpkg_list = get_packages()
    result = []
    for bpkg in bpkg_list:
        record = {"selected_package": False,
                  "package_name": bpkg.full_build_package_name(),
                  "completion_time": bpkg.completion_time.strftime('%Y-%m-%d %H:%M:%S'),           
                  "pkg_id": bpkg.build_pkg.pkg_id,
                  "build_id": bpkg.build_id,
                  }

        result.append(record)
    return result 
    

@csrf_protect
def index(request):
    if request.method == 'POST':
        formset = SelectPackagesFormSet(request.POST)# , initial=initial_data())
        if formset.is_valid():
            action_type = ""
            if "push_packages" in request.POST:
                action_type = "push"
            elif "cancel_packages" in request.POST:
                action_type = "cancel"

            request_list = []
            for form in formset:
                checked         = form.cleaned_data['selected_package']
                if not checked:
                    continue

                # make a list of build_id, build_repo, user
                build_id        = form.cleaned_data['build_id']
                repo_type_id    = form.cleaned_data['repo_type']

                # get build_repo name
                try:
                    build_repo = RepoTypes.objects.get(pk=repo_type_id)
                except:
                    build_repo = None
                
                # get a user
                user = request.user.username
                print("user: %s\treal name: %s" % (request.user, request.user.username))
                request_list.append( (build_id, build_repo, user) )
            push = PushPackagesToRepo(request_list)
            if action_type == 'push':
                push.push_to_repo()
            elif action_type == 'cancel':
                push.cancel_packages()
            #formset = SelectPackagesToPush(initial = initial_data())
            return HttpResponseRedirect('/packages/builds/')
    else:
        formset = SelectPackagesFormSet(initial = initial_data())

    c = {'formset': formset} 
    c.update(csrf(request))

    return render_to_response('packages/builds_form.html', c)

def allbuilds(request):
    c = ""
    return render_to_response('packages/builds.html', c)

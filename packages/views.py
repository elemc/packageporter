from django.template import Context, loader
from django.shortcuts import render_to_response
from packageporter.packages.models import BuildedPackages
from packageporter.repos.models import RepoTypes
from django.http import Http404

from django import forms

from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_protect

from django.forms.formsets import formset_factory

def choice_packages():
    res = []
    for bpkg in get_packages():
        bpkg_list = { "pkg_name": bpkg.full_build_package_name(), 
                      "build_id": bpkg.build_id, 
                      "time": bpkg.completion_time, 
                      "owner": bpkg.owner,
                    }
        bpkg_list = "<td>%s</td>" % bpkg.full_build_package_name()
        res.append( (bpkg.build_id, bpkg_list) )
    #print(res)
    return res
  
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
    #selected_packages = forms.MultipleChoiceField(choices=choice_packages(), widget=forms.CheckboxSelectMultiple())
    selected_package    = forms.BooleanField()
    package_name        = forms.CharField(widget=forms.HiddenInput)
    completion_time     = forms.DateTimeField(widget=forms.HiddenInput)
    repo_type           = forms.ChoiceField(choices=get_all_repo_types())
SelectPackagesFormSet = formset_factory(SelectPackagesToPush)

@csrf_protect
def index(request):
    #try:
    #    bpkg_list = BuildedPackages.objects.filter(pushed=False).order_by('completion_time')
    #except:
    #    raise Http404

    if request.method == 'POST':
        form = SelectPackagesFormSet(request.POST) #SelectPackagesToPush(request.POST)
        if form.is_valid():
            #print(form.cleaned_data['selected_packages'])
            pass
    else:
        bpkg_list = get_packages()
        initial_data = []
        for bpkg in bpkg_list:
            record = {"selected_package": False,
                      "package_name": bpkg.full_build_package_name(),
                      "completion_time": bpkg.completion_time,
                      }

            initial_data.append(record)
        form = SelectPackagesFormSet(initial=initial_data)

    c = {'formset': form} 
    c.update(csrf(request))

    return render_to_response('packages/builds_form.html', c)

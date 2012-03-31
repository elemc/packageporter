from django import forms
from django.forms.formsets import formset_factory
from packageporter.owners.models import Owners
from packageporter.repos.models import Repos,RepoTypes
from packageporter.packages.models import BuildedPackages

class BuildsInitialData(object):
    def __init__(self, request):
        self.request = request

    def get_packages(self):
        try:
            if ( self.request.user.has_perm('packageporter.can_push_all_packages') ):
                bpkg_list = BuildedPackages.objects.filter(pushed=False).order_by('completion_time')
            else:
                print("User name is %s" % self.request.user.username)
                try:
                    owner = Owners.objects.get(owner_name=self.request.user.username)
                except:
                    return []
            
                bpkg_list = BuildedPackages.objects.filter(pushed=False, owner=owner).order_by('completion_time')
        except:
            return []
        return bpkg_list

    def initial_data(self):
        bpkg_list = self.get_packages()
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

    def get(self):
        return self.initial_data()

def get_all_repo_types():
    try:
        r = RepoTypes.objects.all()
    except:
        print("DEBUG: Error in select repo types")
        return []
    
    res = []
    for t in r:
        if (t.rt_id is not None) and (t.rt_name is not None):
            res.append( (t.rt_id, t.rt_name) )
    return res

def get_all_repos():
    try:
        repos = Repos.objects.order_by('repo_name')
    except:
        return []

    result = []
    for repo in repos:
        result.append( (repo.repo_id, repo.repo_name) )

    return result

def get_all_owners():
    try:
        owners = Owners.objects.order_by('owner_name')
    except:
        return []

    result = []
    for owner in owners:
        result.append( (owner.owner_id, owner.owner_name) )
    return result

class SelectPackagesToPush(forms.Form):
    selected_package    = forms.BooleanField(required=False)
    package_name        = forms.CharField(widget=forms.HiddenInput)
    completion_time     = forms.DateTimeField(widget=forms.HiddenInput)
    repo_type           = forms.ChoiceField(choices=get_all_repo_types())
    pkg_id              = forms.IntegerField(widget=forms.HiddenInput)
    build_id            = forms.IntegerField(widget=forms.HiddenInput)
    cancel_reason       = forms.CharField(required=False)
    
SelectPackagesFormSet = formset_factory(SelectPackagesToPush, extra=0)

class PackageForm(forms.Form):
    pkg_id              = forms.IntegerField(required=False, widget=forms.HiddenInput)
    name                = forms.CharField(required=False, widget=forms.HiddenInput)
    owner               = forms.ChoiceField(required=False, choices=get_all_owners(), widget=forms.HiddenInput)
    repo                = forms.ChoiceField(choices=get_all_repos())

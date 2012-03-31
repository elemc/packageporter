from django.template import Context, loader
from django.shortcuts import render_to_response
from packageporter.packages.models import BuildedPackages, Packages
from packageporter.repos.models import Repos

from django.http import Http404, HttpResponseRedirect

from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_protect
from packageporter.oper import PushPackagesToRepo, UpdateFromKoji, ShareOperations
from packageporter.packages.forms import SelectPackagesFormSet, BuildsInitialData, PackageForm

@csrf_protect
@login_required(login_url='/accounts/login/')
def index(request):
    if request.method == 'POST':
        formset = SelectPackagesFormSet(request.POST)
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
				reason          = form.cleaned_data['cancel_reason']

                # get build_repo name
				try:
					build_repo = RepoTypes.objects.get(pk=repo_type_id)
				except:
					build_repo = None
                
                # get a user
				user = request.user.username
				request_list.append( (build_id, build_repo, user, reason) )
			push = PushPackagesToRepo(request_list)
			if action_type == 'push':
				push.push_to_repo()
			elif action_type == 'cancel':
				push.cancel_packages()
			return HttpResponseRedirect('/packages/builds/')
    else:
        ufk = UpdateFromKoji(request.user.username)
        ufk.update_builds()
        bid = BuildsInitialData(request)
        formset = SelectPackagesFormSet(initial = bid.get())

	c = {'formset': formset,
         'user': request.user} 
	c.update(csrf(request))

	return render_to_response('packages/builds_form.html', c)

def allbuilds(request):
    c = ""
    return render_to_response('packages/builds.html', c)

@csrf_protect
@login_required(login_url='/accounts/login/')
def packages(request):
    if not request.user.has_perm('packageporter.can_push_all_packages'):
        allpkgs = Packages.objects.filter(pkg_owner=ShareOperations.get_owner_by_name(request.user.username))
    else:
        allpkgs = Packages.objects.order_by('pkg_name')
    toform = {'user': request.user,
              'packages': allpkgs }
    toform.update(csrf(request))
    return render_to_response('packages/packages.html', toform)

@csrf_protect
@login_required(login_url='/accounts/login/')
def package_edit(request, pkg_id):
    if request.method == 'POST':
        form = PackageForm(request.POST)
        if form.is_valid():
            try:
                pkg = Packages.objects.get(pk=pkg_id)
            except:
                raise Http404

            print(form.cleaned_data['repo'])
            repo_id = form.cleaned_data['repo']
            try:
                repo = Repos.objects.get(pk=repo_id)
            except:
                raise Http404

            pkg.pkg_repo = repo
            pkg.save()
            return HttpResponseRedirect('/packages/')
        else:
            print(form.errors)
    try:
        pkg = Packages.objects.get(pk=pkg_id)
    except Packages.DoesNotExist:
        raise Http404

    init_form = {'pkg_id': pkg_id,
                 'name': pkg.pkg_name,
                 'owner': pkg.pkg_owner.owner_id,
                 'repo': pkg.pkg_repo.repo_id
                 }
    
    form = PackageForm(initial=init_form)

    toform = {'pkg': pkg,
              'form': form}
    toform.update(csrf(request))

    return render_to_response('packages/package_edit.html', toform)

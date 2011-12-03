from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'packageporter.views.home', name='home'),
    url(r'^packages/$', 'packageporter.packages.views.index', name='index'),
    url(r'^packages/builds/$', 'packageporter.packages.views.index', name='index'),
    url(r'^packages/builds/all/$', 'packageporter.packages.views.allbuilds', name='allbuilds'),
    # url(r'^packageporter/', include('packageporter.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
from django.template import Context, loader
from django.shortcuts import render_to_response
from packageporter.oper import UpdateFromKoji

from packageporter.packages.models import BuildOperations

def get_operations():
    bo = BuildOperations.objects.order_by('-operation_time')[:30]
    result = []
    for row in bo:
        build           = row.build.full_build_package_name()
        time            = row.operation_time
        user            = row.operation_user
        oper_type       = row.print_type()
        description     = row.operation_description
        res_row = (build, user, time, oper_type, description)
        result.append(res_row)
    return result

def index(request):
    ufk = UpdateFromKoji()
    ufk.update_builds()

    toform = {'operations': get_operations(),
              'user': request.user}
    
    return render_to_response('index.html', toform)

from django.shortcuts import render_to_response, get_object_or_404
from django.db.models import Q
from wammu_web.wammu.helpers import WammuContext
from wammu_web.phonedb.models import Vendor, Phone, Feature
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.cache import cache

from django.conf import settings

import datetime
from pygooglechart import SimpleLineChart
from pygooglechart import Axis
from pygooglechart import Chart

# Create your views here.

def get_chart_url():
    url = cache.get('phonedb-chart-url')
    if url is not None:
        return url
    enddate = datetime.datetime.now()
    # This works badly, we will rather render only chart for month after
    # it has finished
    #+ datetime.timedelta(days=30)
    endyear = enddate.year
    endmonthlast = enddate.month
    endmonth = 12

    dates = []
    unsupported = []
    supported = []
    totals = []
    alls = []
    years = []

    for year in xrange(2006, endyear + 1):
        if year == endyear:
            endmonth = endmonthlast
        for month in xrange(1, endmonth + 1):
            if month == 1:
                years.append('%d' % year)
            else:
                years.append('')

            time_range = (datetime.date(1900, 1, 1), datetime.date(year, month, 1))

            supported_val = Phone.objects.exclude(state = 'deleted').filter(connection__isnull = False).filter(created__range = time_range).count()
            unsupported_val = Phone.objects.exclude(state = 'deleted').filter(connection__isnull = True).filter(created__range = time_range).count()
            all_val = Phone.objects.filter(created__lt = datetime.date(year, month, 1)).count()

            print '%d-%02d: %d, %d, %d' % (year, month, all_val, supported_val, unsupported_val)
            supported.append(supported_val)
            unsupported.append(unsupported_val)
            totals.append(unsupported_val + supported_val)
            alls.append(all_val)
            dates.append('%d-%02d' % (year, month))

#print dates
#print unsupported
#print supported
#print totals
#print alls

    max_y = ((max(alls) / 100) + 1) * 100

    chart = SimpleLineChart(600, 300, y_range=[0, max_y])


    chart.fill_solid(chart.BACKGROUND, 'ffd480')
    chart.fill_solid(chart.CHART, 'ffd480')
# Chart data
    chart.add_data(supported)
    chart.add_data(totals)
    chart.add_data(alls)
# Lowest value
    chart.add_data([0] * 2)

# Set the line colour to blue
    chart.set_colours(['00FF00', 'FF0000', '0000FF', '00000000'])

#chart.add_fill_range('76A4FB', 2, 3)
# Set the vertical stripes
    month_stripes = 3.0
    chart.fill_linear_stripes(Chart.CHART, 0, 'ffe4a0', month_stripes / len(alls), 'ffd480', month_stripes / len(alls))

# Set the horizontal dotted lines
    chart.set_grid(0, 10, 5, 5)

    chart.set_legend(['Supported phones', 'Valid records', 'Total records'])

    left_axis = map(lambda x: '%d' % x, xrange(0, max_y + 1, max_y / 10))
    left_axis[0] = ''
    chart.set_axis_labels(Axis.LEFT, left_axis)

    chart.set_axis_labels(Axis.BOTTOM, years)

    url = chart.get_url()
    cache.set('phonedb-chart-url', url, 3600)
    return url

def index(request):
    vendors = Vendor.objects.all().order_by('name')
    phones = Phone.objects.filter(state__in = ['approved', 'draft']).order_by('-created')[:settings.PHONES_ON_INDEX]
    return render_to_response('phonedb/index.html', WammuContext(request, {
        'vendors': vendors,
        'phones': phones,
        'features': Feature.objects.all().order_by('name'),
        'chart_url': get_chart_url(),
    }))

def search(request, featurename = None):
    query = request.GET.get('q', None)
    features = request.GET.getlist('feature')

    if featurename is not None:
        features.append(featurename)

    phones = Phone.objects.exclude(state = 'deleted')
    urlparams = []

    # Filter for features
    if len(features) > 0:
        phones = phones.filter(connection__isnull = False)
        for feature in features:
            urlparams.append('feature=%s' % feature)
            phones = phones.filter(features__name = feature)

    # Filter for query string
    if query is not None:
        urlparams.append('q=%s' % query)
        query = query.strip()
        for part in query.split():
            phones = phones.filter(
                Q(vendor__name__icontains = part) |
                Q(name__icontains = part))

    # Sort results
    phones = phones.order_by('vendor__name', 'name')

    paginator = Paginator(phones, settings.PHONES_PER_PAGE, orphans = 5)
    try:
        page = int(request.GET.get('page', '1'))
        if page < 1:
            page = 0
        elif page > paginator.num_pages:
            page = paginator.num_pages
    except ValueError:
        page = 1

    try:
        phones = paginator.page(page)
    except (EmptyPage, InvalidPage):
        phones = paginator.page(1)

    return render_to_response('phonedb/search.html', WammuContext(request, {
        'phones': phones,
        'urlparams': '&'.join(urlparams),
    }))

def vendor(request, vendorname):
    vendor = get_object_or_404(Vendor, slug = vendorname)
    phones = Phone.objects.filter(vendor = vendor, state = 'approved').order_by('name')

    paginator = Paginator(phones, settings.PHONES_PER_PAGE, orphans = 5)
    try:
        page = int(request.GET.get('page', '1'))
        if page < 1:
            page = 0
        elif page > paginator.num_pages:
            page = paginator.num_pages
    except ValueError:
        page = 1

    try:
        phones = paginator.page(page)
    except (EmptyPage, InvalidPage):
        phones = paginator.page(1)

    return render_to_response('phonedb/vendor.html', WammuContext(request, {
        'vendor': vendor,
        'phones': phones,
    }))

def phone(request, vendorname, id):
    id = int(id)
    vendor = get_object_or_404(Vendor, slug = vendorname)
    phone = get_object_or_404(Phone, id = id, vendor = vendor)
    related = Phone.objects.filter(vendor = vendor, name__icontains = phone.name, state = 'approved').exclude(id = id)
    return render_to_response('phonedb/phone.html', WammuContext(request, {
        'vendor': vendor,
        'phone': phone,
        'related': related,
    }))

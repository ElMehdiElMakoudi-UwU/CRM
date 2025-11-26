from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Client, ClientSegment
from .forms import ClientForm, ClientSegmentForm

from django.views.generic import ListView
from django.db.models import Q
from .models import Client

import pandas as pd
from django.http import HttpResponse
from .models import Client
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from .models import Client
from io import BytesIO
from django.db.models import Count



# =========================
# CLIENT VIEWS
# =========================

class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 50

    def get_queryset(self):
        query = self.request.GET.get('search', '')
        segment = self.request.GET.get('segment', '')
        
        # Filter clients based on user role
        # Managers and admins see all clients, sales reps only see their own
        user_role = self.request.user.profile.role if hasattr(self.request.user, 'profile') else None
        if user_role in ['manager', 'admin']:
            qs = Client.objects.all()
        else:
            # Sales reps only see clients they created
            qs = Client.objects.filter(created_by=self.request.user)

        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query))
        if segment:
            qs = qs.filter(segment=segment)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['segments'] = Client.objects.values_list('segment', flat=True).distinct()
        return context

class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'
    
    def get_queryset(self):
        # Filter clients based on user role
        user_role = self.request.user.profile.role if hasattr(self.request.user, 'profile') else None
        if user_role in ['manager', 'admin']:
            return Client.objects.all()
        else:
            # Sales reps only see clients they created
            return Client.objects.filter(created_by=self.request.user)

class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('clients:client_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('clients:client_list')
    
    def get_queryset(self):
        # Filter clients based on user role
        user_role = self.request.user.profile.role if hasattr(self.request.user, 'profile') else None
        if user_role in ['manager', 'admin']:
            return Client.objects.all()
        else:
            # Sales reps can only update clients they created
            return Client.objects.filter(created_by=self.request.user)

class ClientDeleteView(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = 'clients/client_confirm_delete.html'
    success_url = reverse_lazy('clients:client_list')
    
    def get_queryset(self):
        # Filter clients based on user role
        user_role = self.request.user.profile.role if hasattr(self.request.user, 'profile') else None
        if user_role in ['manager', 'admin']:
            return Client.objects.all()
        else:
            # Sales reps can only delete clients they created
            return Client.objects.filter(created_by=self.request.user)

def client_export_excel(request):
    # Filter clients based on user role
    user_role = request.user.profile.role if hasattr(request.user, 'profile') else None
    if user_role in ['manager', 'admin']:
        clients = Client.objects.all().values('name', 'phone', 'email', 'balance', 'segment')
    else:
        clients = Client.objects.filter(created_by=request.user).values('name', 'phone', 'email', 'balance', 'segment')

    df = pd.DataFrame(clients)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="clients.xlsx"'

    df.to_excel(response, index=False)

    return response

def client_export_pdf(request):
    # Filter clients based on user role
    user_role = request.user.profile.role if hasattr(request.user, 'profile') else None
    if user_role in ['manager', 'admin']:
        clients = Client.objects.all()
    else:
        clients = Client.objects.filter(created_by=request.user)

    template = get_template('clients/pdf_template.html')
    html = template.render({'clients': clients})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="clients.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Une erreur est survenue lors de la génération du PDF', status=500)

    return response


# =========================
# CLIENT SEGMENT VIEWS
# =========================

class SegmentListView(LoginRequiredMixin, ListView):
    model = ClientSegment
    template_name = 'clients/segment_list.html'
    context_object_name = 'segments'


class SegmentListView(LoginRequiredMixin, ListView):
    model = ClientSegment
    template_name = 'clients/segment_list.html'
    context_object_name = 'segments'

    def get_queryset(self):
        return ClientSegment.objects.annotate(client_count=Count('clients')).order_by('name')


class SegmentCreateView(LoginRequiredMixin, CreateView):
    model = ClientSegment
    form_class = ClientSegmentForm
    template_name = 'clients/segment_form.html'
    success_url = reverse_lazy('clients:segment_list')


class SegmentUpdateView(LoginRequiredMixin, UpdateView):
    model = ClientSegment
    form_class = ClientSegmentForm
    template_name = 'clients/segment_form.html'
    success_url = reverse_lazy('clients:segment_list')


class SegmentDeleteView(LoginRequiredMixin, DeleteView):
    model = ClientSegment
    template_name = 'clients/segment_confirm_delete.html'
    success_url = reverse_lazy('clients:segment_list')


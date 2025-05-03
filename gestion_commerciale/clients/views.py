from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Client, ClientSegment
from .forms import ClientForm, ClientSegmentForm


# =========================
# CLIENT VIEWS
# =========================

class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 20


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'


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


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = 'clients/client_confirm_delete.html'
    success_url = reverse_lazy('clients:client_list')


# =========================
# CLIENT SEGMENT VIEWS
# =========================

class SegmentListView(LoginRequiredMixin, ListView):
    model = ClientSegment
    template_name = 'clients/segment_list.html'
    context_object_name = 'segments'


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


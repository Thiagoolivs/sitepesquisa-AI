from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('pesquisa', views.pesquisa, name='pesquisa'),
    path('ia', views.ia_page, name='ia'),
    path('analisar', views.analisar, name='analisar'),
    path('analisar_dados', views.analisar_dados, name='analisar_dados'),
    path('upload_csv', views.upload_csv, name='upload_csv'),
    path('formulario', views.formulario_api, name='formulario'),
    path('formulario/responder', views.formulario_responder, name='formulario_responder'),
    path('formulario/dados', views.formulario_dados, name='formulario_dados'),
    path('formulario/analise', views.formulario_analise, name='formulario_analise'),
    path('ia_api', views.ia_api, name='ia_api'),
    path('ia_csv', views.ia_csv, name='ia_csv'),
]

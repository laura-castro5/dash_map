import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy import stats
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from shapely.geometry import Polygon

# Configuração da página
st.set_page_config(layout="wide", page_title="Monitoramento da Água - Bacia do Pericumã")
st.title("🌊 Monitoramento da Superfície de Água")
st.subheader("Bacia Hidrográfica do Rio Pericumã")

# 1. Carregamento do shapefile da bacia
@st.cache_data
def load_basin_shape():
    """Carrega o shapefile da bacia do Pericumã"""
    try:
        # Verifica se o arquivo existe
        shapefile_path = 'assets/Bacia_Pericuma_ZEE_v2.shp'
        if not os.path.exists(shapefile_path):
            st.error("Shapefile não encontrado no caminho especificado")
            return None
        
        # Carrega o shapefile
        gdf = gpd.read_file(shapefile_path)
        
        # Verifica se tem o CRS definido (importante para cálculos de área)
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
            
        return gdf
    
    except Exception as e:
        st.error(f"Erro ao carregar shapefile: {str(e)}")
        return None

# 2. Carregamento de dados simulados (substituir por API MapBiomas)
@st.cache_data
def load_water_data(years):
    """Gera dados simulados de área de água baseados no shapefile"""
    try:
        # Baseado na área da bacia (simulação)
        basin_area = 2500  # Valor hipotético em km²
        base_water = 0.15  # 15% da área como água em média
        
        # Gera dados com tendência e sazonalidade - CORREÇÃO DA LINHA 51
        areas = base_water * basin_area * (1 + 0.005*(np.array(years)-1985) + 
                0.1 * np.sin(2*np.pi*(np.array(years)-1985)/10))
        
        return pd.DataFrame({
            'Ano': years,
            'Área (km²)': np.round(areas, 2),
            'Porcentagem (%)': np.round(areas/basin_area*100, 2),
            'Tipo': 'Água'
        })
    except Exception as e:
        st.error(f"Erro ao gerar dados simulados: {str(e)}")
        return None

# Carrega os dados
basin_gdf = load_basin_shape()
years = list(range(1985, 2024))
df_water = load_water_data(years)

# Fallback para dados simplificados se necessário
if basin_gdf is None:
    st.warning("Usando polígono simplificado para demonstração")
    coords = [(-44.5, -2.0), (-44.0, -2.0), (-44.0, -2.5), (-44.5, -2.5), (-44.5, -2.0)]
    basin_gdf = gpd.GeoDataFrame({'geometry': [Polygon(coords)], 'name': ['Bacia do Pericumã (simplificada)']})

if df_water is None:
    st.warning("Usando dados simulados básicos")
    df_water = pd.DataFrame({
        'Ano': years,
        'Área (km²)': 200 + 5*(np.array(years)-1985),
        'Porcentagem (%)': 8 + 0.2*(np.array(years)-1985),
        'Tipo': 'Água'
    })


# 3. Sidebar com controles
with st.sidebar:
    st.header("⚙️ Configurações")
    
    selected_year = st.selectbox(
        "Ano para análise:",
        options=sorted(df_water['Ano'], reverse=True),
        index=0
    )
    
    analysis_type = st.radio(
        "Tipo de visualização:",
        options=["Área Absoluta", "Porcentagem da Bacia"],
        index=0
    )
    
    show_trend = st.checkbox("Mostrar tendência", True)
    show_stats = st.checkbox("Mostrar estatísticas detalhadas", True)

# 4. Visualização do mapa
st.subheader("🗺️ Mapa da Bacia Hidrográfica")

col1, col2 = st.columns([2, 1])

with col1:
    fig, ax = plt.subplots(figsize=(10, 6))
    basin_gdf.plot(ax=ax, color='lightblue', edgecolor='navy', linewidth=1)
    
    # Adiciona título e informações
    ax.set_title("Bacia do Rio Pericumã", fontsize=14)
    ax.annotate(f"Área: {basin_gdf.geometry.area.sum()/1e6:.1f} km²", 
               xy=(0.5, 0.05), xycoords='axes fraction',
               ha='center', fontsize=10, bbox=dict(boxstyle="round", alpha=0.1))
    
    ax.set_axis_off()
    st.pyplot(fig)

with col2:
    st.markdown("**Características da Bacia:**")
    st.write(f"- Área total: {basin_gdf.geometry.area.sum()/1e6:.1f} km²")
    
    if 'name' in basin_gdf.columns:
        st.write(f"- Nome: {basin_gdf['name'].iloc[0]}")
    
    st.write(f"- Sistema de referência: {basin_gdf.crs}")
    
    st.markdown("**Dados de Água:**")
    current_data = df_water[df_water['Ano'] == selected_year].iloc[0]
    st.write(f"- {selected_year}: {current_data['Área (km²)']:.1f} km²")
    st.write(f"- {selected_year}: {current_data['Porcentagem (%)']:.1f}% da bacia")

# 5. Visualização temporal - VERSÃO ALINHADA COM EARTH ENGINE
st.subheader("📈 Evolução Temporal")

# Seleciona a métrica para visualização
y_metric = 'Área (km²)' if analysis_type == "Área Absoluta" else 'Porcentagem (%)'
y_title = 'Área de Água (km²)' if analysis_type == "Área Absoluta" else 'Porcentagem da Bacia (%)'

fig = go.Figure()

# Adiciona os dados principais como barras (igual ao Earth Engine)
fig.add_trace(go.Bar(
    x=df_water['Ano'],
    y=df_water[y_metric],
    name='Área de Água',
    marker_color='#1d4e89',
    opacity=0.8,
    hovertemplate="Ano: %{x}<br>" + y_title + ": %{y:.2f}<extra></extra>"
))

# SEÇÃO DE TENDÊNCIA - AJUSTADA PARA O MÉTODO DO EARTH ENGINE
if show_trend:
    # Calcula a tendência linear (mesmo método que no Earth Engine)
    x = df_water['Ano'].astype(int) - 1985  # Normaliza os anos começando em 0
    y = df_water[y_metric]
    
    n = len(x)
    sum_x = x.sum()
    sum_y = y.sum()
    sum_xy = (x * y).sum()
    sum_x2 = (x**2).sum()
    
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
    intercept = (sum_y - slope * sum_x) / n
    
    # Gera os valores da tendência
    trend = intercept + slope * x
    
    # Adiciona a linha de tendência (vermelha como no Earth Engine)
    fig.add_trace(go.Scatter(
        x=df_water['Ano'],
        y=trend,
        mode='lines',
        name='Tendência',
        line=dict(color='#ff6b6b', width=3),
        hovertemplate="Tendência: %{y:.2f}<extra></extra>"
    ))
    
    # Adiciona estatísticas no sidebar (opcional)
    with st.sidebar.expander("📊 Estatísticas da Tendência"):
        st.write(f"**Inclinação:** {slope:.4f} {'km²/ano' if analysis_type == 'Área Absoluta' else '%/ano'}")
        st.write(f"**Intercepto:** {intercept:.2f}")
        st.write(f"**Variação total:** {(trend.iloc[-1] - trend.iloc[0]):.2f} {'km²' if analysis_type == 'Área Absoluta' else '%'}")
        st.write(f"**Taxa média anual:** {slope:.2f} {'km²/ano' if analysis_type == 'Área Absoluta' else '%/ano'}")

# Destaca o ano selecionado
fig.add_vrect(
    x0=selected_year-0.5, x1=selected_year+0.5,
    fillcolor="green", opacity=0.1, line_width=0,
    annotation_text=f"Ano {selected_year}", annotation_position="top left"
)

# Configurações do layout (ajustadas para combinar com o estilo do Earth Engine)
fig.update_layout(
    title=f'Evolução da Superfície de Água (1985-2023) - {analysis_type}',
    xaxis_title='Ano',
    yaxis_title=y_title,
    hovermode='x unified',
    height=500,
    template='plotly_white',
    barmode='group',
    bargap=0.2,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

st.plotly_chart(fig, use_container_width=True)

# 6. Métricas principais
st.subheader("📊 Métricas Principais")

current_data = df_water[df_water['Ano'] == selected_year].iloc[0]
mean_area = df_water['Área (km²)'].mean()
mean_perc = df_water['Porcentagem (%)'].mean()

col1, col2, col3 = st.columns(3)

col1.metric(
    f"Área em {selected_year}",
    f"{current_data['Área (km²)']:.1f} km²",
    f"{current_data['Área (km²)'] - mean_area:+.1f} km² vs média"
)

col2.metric(
    f"Porcentagem em {selected_year}",
    f"{current_data['Porcentagem (%)']:.1f}%",
    f"{current_data['Porcentagem (%)'] - mean_perc:+.1f}% vs média"
)

max_year = df_water.loc[df_water['Área (km²)'].idxmax(), 'Ano']
col3.metric(
    "Ano com maior área",
    f"{max_year}",
    f"{df_water['Área (km²)'].max():.1f} km²"
)

# 7. Análise estatística detalhada
if show_stats:
    st.subheader("📉 Análise Estatística")
    
    x = df_water['Ano']
    y = df_water[y_metric]
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Tendência Temporal:**")
        st.write(f"- Variação anual: {slope:.3f} {'km²/ano' if analysis_type == 'Área Absoluta' else '%/ano'}")
        st.write(f"- Significância (p-valor): {p_value:.4f}")
        st.write(f"- Coeficiente de determinação (R²): {r_value**2:.3f}")
        
    with col2:
        st.markdown("**Estatísticas Descritivas:**")
        st.write(f"- Média: {y.mean():.2f} {'km²' if analysis_type == 'Área Absoluta' else '%'}")
        st.write(f"- Desvio padrão: {y.std():.2f} {'km²' if analysis_type == 'Área Absoluta' else '%'}")
        st.write(f"- Variação total: {(y.max() - y.min())/y.min()*100:.1f}%")

# 8. Tabela de dados
st.subheader("📋 Dados Completos")
st.dataframe(
    df_water.style.format({
        'Área (km²)': '{:.2f}',
        'Porcentagem (%)': '{:.2f}'
    }).background_gradient(subset=['Área (km²)', 'Porcentagem (%)'], cmap='Blues'),
    height=400,
    use_container_width=True
)

# 9. Download dos dados
csv = df_water.to_csv(index=False).encode('utf-8')
st.download_button(
    label="⬇️ Baixar dados como CSV",
    data=csv,
    file_name='area_agua_pericuma.csv',
    mime='text/csv'
)

# 10. Informações sobre os dados
with st.expander("ℹ️ Sobre os dados e implementação"):
    st.markdown("""
    ### Como implementar com dados reais:
    
    1. **Substitua a função `load_water_data()`** para conectar com a API do MapBiomas ou ler dados pré-baixados.
    
    2. **Estrutura do projeto:**
    ```
    seu_projeto/
    ├── app.py               # Este script
    ├── assets/
    │   └── Bacia_Pericuma_ZEE_v2.shp  # Shapefile principal
    │   └── Bacia_Pericuma_ZEE_v2.shx  # Arquivos auxiliares
    │   └── Bacia_Pericuma_ZEE_v2.dbf  # do shapefile
    ```
    
    3. **Para produção:**
       - Adicione autenticação se necessário
       - Considere cachear os dados localmente
       - Implemente tratamento de erros robusto
    """)
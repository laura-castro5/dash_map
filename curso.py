import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import folium_static

@st.cache_data
def load_geodata():
    """Carrega o arquivo GeoJSON com os polígonos dos estados brasileiros"""
    return gpd.read_file('assets/BR_UF_2020_filtrado.geojson')

@st.cache_data
def load_data():
    """Carrega os dados de seguros no formato Parquet"""
    return pd.read_parquet('assets/dados_test.parquet')

gdf = load_geodata()

df = load_data()

cols_numericas = ['NR_AREA_TOTAL', 'VL_PREMIO_LIQUIDO']

df[cols_numericas] = df[cols_numericas].replace(',', '.', regex=True).astype(float)

df_estado = df.groupby('SG_UF_PROPRIEDADE').agg(
    area_total=('NR_AREA_TOTAL', 'sum'),
    valor_total=('VL_PREMIO_LIQUIDO', 'sum'),
    numero_seguros=('NR_APOLICE', 'nunique')
).reset_index()

gdf_merged = gdf.merge(
    df_estado,
    left_on='SIGLA_UF',
    right_on='SG_UF_PROPRIEDADE',
    how='left'
)

df_razao_social = df.groupby('NM_RAZAO_SOCIAL').agg(
    numero_seguros=('NR_APOLICE', 'nunique'),
    area_total=('NR_AREA_TOTAL', 'sum'),
    valor_total=('VL_PREMIO_LIQUIDO', 'sum'),
    estados=('SG_UF_PROPRIEDADE', 'unique')  # array com estados únicos
).reset_index()

df_razao_social['contagem_estados'] = df_razao_social['estados'].apply(len)

df_razao_social_estado = df.groupby(['NM_RAZAO_SOCIAL', 'SG_UF_PROPRIEDADE']).agg(
    numero_seguros=('NR_APOLICE', 'nunique'),
    area_total=('NR_AREA_TOTAL', 'sum'),
    valor_total=('VL_PREMIO_LIQUIDO', 'sum')
).reset_index()

cols_correlacao = [
    'NR_AREA_TOTAL',
    'VL_PREMIO_LIQUIDO',
    'VL_LIMITE_GARANTIA',
    'NR_PRODUTIVIDADE_ESTIMADA',
    'NR_PRODUTIVIDADE_SEGURADA',
    'VL_SUBVENCAO_FEDERAL'
]

for col in cols_correlacao:
    if col in df.columns:  # Verifica se a coluna existe no DataFrame
        # Converte vírgula para ponto e transforma em float
        df[col] = df[col].replace(',', '.', regex=True).astype(float)
        
correlation_matrix = df[cols_correlacao].corr().round(2)

with st.sidebar:
    st.image('assets/lageos.jpeg', width=210)
    st.subheader('SISSER - Sistema de Subvenção Econômica')
    analise_tipo = st.selectbox(
        "Selecione o tipo de análise",
        ["Razão Social", "Estado"]  
    )
    
top_estado_num = df_estado.loc[df_estado['numero_seguros'].idxmax()]
top_estado_area = df_estado.loc[df_estado['area_total'].idxmax()]
top_estado_valor = df_estado.loc[df_estado['valor_total'].idxmax()]

st.markdown(f"""
    *Destaques por Estado:*
    - 🏆 Maior nº apólices: {top_estado_num['SG_UF_PROPRIEDADE']} ({top_estado_num['numero_seguros']})
    - 📏 Maior área: {top_estado_area['SG_UF_PROPRIEDADE']} ({top_estado_area['area_total']:,.2f} ha)
    - 💰 Maior valor: {top_estado_valor['SG_UF_PROPRIEDADE']} (R$ {top_estado_valor['valor_total']:,.2f})
    """)

st.title("Análise de Seguros Agrícolas - SISSER")
st.markdown("""
*Sistema de Subvenção Econômica ao Prêmio do Seguro Rural*
Dados atualizados em 2023
""")
st.divider()

            
try:
    # Define qual coluna usar para hover (depende do dataset)
    hover_col = 'NM_UF' if 'NM_UF' in gdf_merged.columns else 'SIGLA_UF'

    fig_map = px.choropleth(
        gdf_merged,
        geojson=gdf_merged.geometry,
        locations=gdf_merged.index,
        color='numero_seguros',
        hover_name=hover_col,
        hover_data=['area_total', 'valor_total'],
        color_continuous_scale="Blues",
        projection="mercator",
        title="Distribuição Geográfica de Apólices por Estado"
    )

    fig_map.update_geos(fitbounds="locations", visible=False)

    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})

    fig_map.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>"
                     "Apólices: %{z}<br>"
                     "Área: %{customdata[0]:,.2f} ha<br>"
                     "Valor: R$ %{customdata[1]:,.2f}"
    )

    st.plotly_chart(fig_map, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao gerar o mapa: {str(e)}")
    st.write("Dados disponíveis para mapeamento:", gdf_merged.columns.tolist())

st.divider()

if analise_tipo == "Razão Social":
    st.header("Análise por Razão Social")

    metric_options = {
        'Número de Seguros': 'numero_seguros',
        'Contagem de Estados': 'contagem_estados',
        'Área Total': 'area_total',
        'Valor Total': 'valor_total'
    }
    
    # Cria selectbox para escolher a métrica
    selected_metric = st.selectbox(
        "Selecione a Métrica",
        options=list(metric_options.keys())
    )
    metric_column = metric_options[selected_metric]
    df_sorted = df_razao_social.sort_values(by=metric_column, ascending=False)
    
fig_bar = px.bar(
        df_sorted,
        x='NM_RAZAO_SOCIAL',
        y=metric_column,
        title=f'{selected_metric} por Razão Social',
        labels={
            'NM_RAZAO_SOCIAL': 'Razão Social',
            metric_column: selected_metric
        }
    )

st.plotly_chart(fig_bar, use_container_width=True)

# Seção de indicadores principais
st.subheader("Principais Indicadores")

    # Cria 4 colunas para exibir métricas lado a lado
col1, col2, col3, col4 = st.columns(4)

with col1:
        # Número total de empresas
        st.metric("Total Empresas", len(df_razao_social))

with col2:
        # Soma total de apólices
        st.metric("Total Apólices", df_razao_social['numero_seguros'].sum())

with col3:
        # Soma total da área (formatada com separador de milhares)
        st.metric("Área Total (ha)", f"{df_razao_social['area_total'].sum():,.2f}")

with col4:
        # Soma total do valor (formatado como moeda)
        st.metric("Valor Total (R$)", f"{df_razao_social['valor_total'].sum():,.2f}")

st.divider()

st.header("Análise de Correlações")

fig_heatmap = px.imshow(
    correlation_matrix,
    text_auto=True,
    color_continuous_scale="Blues",
    title="Correlação entre Variáveis",
    width=800,
    height=600
)

st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("""
*Interpretação:*
- Valores próximos a *1* indicam forte correlação positiva
- Valores próximos a *-1* indicam forte correlação negativa
- Valores próximos a *0* indicam pouca ou nenhuma correlação
""")

st.divider()

st.header("Distribuição de Valores")

tab1, tab2, tab3 = st.tabs(["Área Total", "Valor Total", "Apólices por Estado"])

with tab1:
    fig_area = px.pie(
        df_razao_social,
        names='NM_RAZAO_SOCIAL',
        values='area_total',
        title='Distribuição da Área Total por Empresa'
    )
    st.plotly_chart(fig_area, use_container_width=True)
    
with tab2:
    # Gráfico de pizza mostrando distribuição do valor por empresa
    fig_valor = px.pie(
        df_razao_social,
        names='NM_RAZAO_SOCIAL',
        values='valor_total',
        title='Distribuição do Valor Total por Empresa'
    )
    st.plotly_chart(fig_valor, use_container_width=True)
    
with tab3:
    # Gráfico de barras mostrando número de apólices por estado
    fig_estado = px.bar(
        df_estado.sort_values('numero_seguros', ascending=False),
        x='SG_UF_PROPRIEDADE',
        y='numero_seguros',
        title='Número de Apólices por Estado'
    )
    st.plotly_chart(fig_estado, use_container_width=True)
    
st.divider()

st.markdown("""
*Fonte dos dados:* [SISSER](https://dados.gov.br/dados/conjuntos-dados/sisser-sistema-de-subvencao-economica-ao-premio-do-seguro-rural)
*Última atualização:* 2023
*Desenvolvido por:* Laura Castro
""")
    
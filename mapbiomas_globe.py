# Bibliotecas principais
import geemap
import ee
import streamlit as st
import pandas as pd
import plotly.express as px
import json

import ee
ee.Authenticate()  # Vai abrir uma janela para login/autorização

# Configuração da página
st.set_page_config(
    page_title="MapBiomas Coleção 9 - Acesso Alternativo",
    page_icon="🌎",
    layout="wide"
)

# Inicialização do Earth Engine
if not ee.data._initialized:
    try:
        ee.Initialize()
    except Exception as e:
        st.error(f"Erro ao inicializar o Earth Engine: {str(e)}")
        st.info("Por favor, autentique-se no Google Earth Engine primeiro.")
        ee.Authenticate()
        ee.Initialize()

# Título e introdução
st.title('APP LAGEOS - MAPBIOMAS COLEÇÃO 9 (ACESSO ALTERNATIVO)')
st.write("""
    Esta versão utiliza uma abordagem alternativa para acessar os dados do MapBiomas,
    contornando problemas de permissão. Série histórica de 1985 a 2023 disponível.
    
    **Fonte técnica**: [MapBiomas API](https://mapbiomas.org/api)
""")

# Função para carregar os dados do MapBiomas sem depender do projeto restrito
@st.cache_data
def load_mapbiomas_alternative():
    try:
        # Criamos uma imagem base
        years = range(1985, 2024)
        images = []
        
        for year in years:
            # ✅ Caminho corrigido sem o 'public'
            img = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')  \
                  .select(f'classification_{year}')
            images.append(img)
        
        # Combina as bandas
        final_image = ee.Image.cat(images)
        return final_image
    except Exception as e:
        st.error(f"Erro na abordagem alternativa: {str(e)}")
        return None
# Carrega os dados
mapbiomas_image = load_mapbiomas_alternative()

if mapbiomas_image is None:
    st.error("""
        Não foi possível carregar os dados mesmo com a abordagem alternativa.
        Entre em contato com o administrador do sistema.
    """)
    st.stop()

# Definição das classes e cores (mesmo esquema anterior)
CLASSES = {
    1: "Formação Florestal",
    2: "Formação Natural não Florestal",
    3: "Agropecuária",
    4: "Área não Vegetada",
    5: "Corpo D'água",
    6: "Não Observado"
}

PALETTE = [
    '#006400', '#B8AF4F', '#FFD966', 
    '#E974ED', '#0000FF', '#FFFFFF'
]

# Mapeamento de classes
CLASS_MAPPING = {
    **{code: 1 for code in [1, 3, 4, 5, 6, 49]},
    **{code: 2 for code in [10, 11, 12, 32, 29, 50]},
    **{code: 3 for code in [14, 15, 18, 19, 39, 20, 40, 62, 41, 36, 46, 47, 35, 48, 9, 21]},
    **{code: 4 for code in [22, 23, 24, 30, 25]},
    **{code: 5 for code in [26, 33, 31]},
    **{code: 6 for code in [27]}
}

# Interface do usuário
st.sidebar.header("Configurações")

# Seleção de anos
years = list(range(1985, 2024))
selected_years = st.sidebar.multiselect(
    'Selecione os anos para análise',
    years,
    default=[2020, 2023]
)

# Área de estudo
st.sidebar.header("Área de Interesse")
geometry_option = st.sidebar.radio(
    "Escolha a área:",
    ["Brasil Inteiro", "Personalizada"]
)

geometry = None
if geometry_option == "Personalizada":
    with st.sidebar.expander("Defina sua área"):
        st.info("Use coordenadas no formato GeoJSON")
        geojson_input = st.text_area("Cole seu GeoJSON aqui:")
        
        if geojson_input:
            try:
                geo_dict = json.loads(geojson_input)
                geometry = ee.Geometry(geo_dict)
                st.success("Área definida com sucesso!")
            except Exception as e:
                st.error(f"Erro no GeoJSON: {str(e)}")
else:
    # Área padrão (Brasil inteiro)
    geometry = ee.Geometry.Rectangle([-74, -34, -35, 6])

# Processamento principal
def process_data():
    # Criar mapa
    m = geemap.Map(center=[-15, -55], zoom=4)
    
    # Adicionar área de estudo
    if geometry:
        m.addLayer(geometry, {'color': 'red'}, "Área de Estudo")
        m.centerObject(geometry, zoom=6)
    
    # Processar cada ano selecionado
    for year in selected_years:
        band_name = f"classification_{year}"
        
        try:
            # Verificar se a banda existe
            if band_name not in mapbiomas_image.bandNames().getInfo():
                st.warning(f"Dados para {year} não disponíveis")
                continue
            
            # Selecionar e processar a banda
            band = mapbiomas_image.select(band_name)
            remapped = band.remap(
                list(CLASS_MAPPING.keys()),
                list(CLASS_MAPPING.values())
            )  # Parêntese fechado corretamente
            
            if geometry:
                remapped = remapped.clip(geometry)
            
            # Adicionar ao mapa
            m.addLayer(
                remapped,
                {'min': 1, 'max': 6, 'palette': PALETTE},
                f"MapBiomas {year}"
            )
        except Exception as e:
            st.error(f"Erro no ano {year}: {str(e)}")
    
    # Exibir mapa
    st.subheader("Visualização do Mapa")
    m.to_streamlit(height=600)
    
    # Cálculo de áreas
    if len(selected_years) > 0:
        st.subheader("Análise de Áreas")
        
        with st.spinner("Calculando áreas..."):
            results = []
            for year in selected_years:
                band_name = f"classification_{year}"
                band = mapbiomas_image.select(band_name)
                remapped = band.remap(
                    list(CLASS_MAPPING.keys()),
                    list(CLASS_MAPPING.values()))
                
                if geometry:
                    remapped = remapped.clip(geometry)
                
                for class_id, class_name in CLASSES.items():
                    area = remapped.eq(class_id).multiply(ee.Image.pixelArea())
                    stats = area.reduceRegion(
                        reducer=ee.Reducer.sum(),
                        geometry=geometry,
                        scale=30,
                        maxPixels=1e13
                    )
                    area_km2 = stats.get(band_name).getInfo() / 1e6
                    results.append({
                        'Ano': year,
                        'Classe': class_name,
                        'Área (km²)': round(area_km2, 2)
                    })
            
            if results:
                df = pd.DataFrame(results)
                
                # Exibir resultados
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.dataframe(df)
                
                with col2:
                    if len(selected_years) > 1:
                        fig = px.line(
                            df, x='Ano', y='Área (km²)', color='Classe',
                            title='Evolução Temporal',
                            color_discrete_sequence=PALETTE
                        )
                    else:
                        fig = px.pie(
                            df, values='Área (km²)', names='Classe',
                            title=f'Distribuição {selected_years[0]}',
                            color_discrete_sequence=PALETTE
                        )
                    st.plotly_chart(fig, use_container_width=True)

# Executar o processamento
process_data()

# Rodapé
st.markdown("---")
st.markdown("""
    **Créditos**: 
    - Dados: MapBiomas Coleção 9
    - Plataforma: Google Earth Engine
    - Desenvolvido por: LAGEOS/UFRJ
""")
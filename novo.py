import streamlit as st  # Para criar a interface web
import geemap.foliumap as geemap  # Para visualização de mapas
import ee  # Google Earth Engine
import json  # Para trabalhar com dados JSON
import pandas as pd  # Para manipulação de dados
import geopandas as gpd  # Para dados geoespaciais
import tempfile  # Para criar arquivos temporários
import os  # Para operações com sistema de arquivos
import plotly.express as px  # Para gráficos interativos
import matplotlib.pyplot as plt  # Para gráficos estáticos

# Inicialização do Earth Engine
try:
    ee.Initialize(project='ee-laurahelenna')  # Tenta inicializar com o projeto existente
except Exception as e:
    try:
        ee.Authenticate()  # Se falhar, tenta autenticar
        ee.Initialize(project='ee-laurahelenna')  # E inicializa novamente
    except:
        st.warning("Falha na autenticação do Earth Engine. Verifique suas credenciais.")
        
# Configuração da página do Streamlit
st.set_page_config(layout='wide')  # Layout amplo para melhor utilização do espaço
st.title("🌱 APP MAPBIOMAS LAGEOS/LAB - MARANHÃO")  # Título do aplicativo
st.write("Análise de cobertura do solo para municípios do Maranhão usando MapBiomas Collection 9")  # Descrição

# Carregar GeoJSON com municípios do Maranhão
try:
    with open('assets/municipios_ma.geojson', 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)  # Carrega o arquivo GeoJSON
        st.success("Arquivo GeoJSON carregado com sucesso!")  # Mensagem de sucesso
except Exception as e:
    st.error(f"Erro ao carregar GeoJSON: {str(e)}")  # Mensagem de erro se falhar
    geojson_data = None  # Define como None se houver erro
    
# Função para carregar os municípios (cacheada para melhor performance)
@st.cache_resource
def load_municipios():
    municipios = {}  # Dicionário para armazenar os municípios
    if geojson_data:  # Se o GeoJSON foi carregado com sucesso
        for feature in geojson_data['features']:  # Itera sobre cada feature
            nome = feature['properties'].get('NM_MUNICIP')  # Obtém o nome do município
            if nome:
                municipios[nome] = feature['geometry']  # Armazena a geometria do município
    return municipios  # Retorna o dicionário de municípios

MUNICIPIOS_MA = load_municipios()  # Carrega os municípios

# Configurações do MapBiomas - Versão expandida com mais classes
CLASS_CONFIG = {
    'codes': [0, 1, 3, 4, 5, 6, 49, 10, 11, 12, 32, 29, 50, 14, 15, 18, 19, 39, 20, 40, 62, 41, 36, 46, 47, 35, 48, 9, 21, 22, 23, 24, 30, 25, 26, 33, 31, 27],
    'new_classes': [0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 6],
    'palette': [
        '#ffffff',  # 0 - Não Observado
        '#1f8d49',  # 1 - Floresta (Formação Florestal)
        '#7dc975',  # 1 - Floresta (Formação Savânica)
        '#04381d',  # 1 - Floresta (Mangue)
        '#007785',  # 1 - Floresta (Floresta Alagável)
        '#02d659',  # 1 - Floresta (Restinga Arbórea)
        '#d6bc74',  # 2 - Vegetação Herbácea (Formação Campestre)
        '#519799',  # 2 - Vegetação Herbácea (Campo Alagado)
        '#fc8114',  # 2 - Vegetação Herbácea (Apicum)
        '#ffaa5f',  # 2 - Vegetação Herbácea (Afforamento Rochoso)
        '#ad5100',  # 2 - Vegetação Herbácea (Restinga Herbácea)
        '#ffefc3',  # 3 - Agropecuária (Agricultura)
        '#edde8e',  # 3 - Agropecuária (Pastagem)
        '#E974ED',  # 3 - Agropecuária (Lavouras Temporárias)
        '#C27BA0',  # 3 - Agropecuária (Soja)
        '#db7093',  # 3 - Agropecuária (Cana)
        '#c71585',  # 3 - Agropecuária (Arroz)
        '#ff69b4',  # 3 - Agropecuária (Algodão)
        '#f54ca9',  # 3 - Agropecuária (Outras Lavouras Temporárias)
        '#d082de',  # 3 - Agropecuária (Lavouras Perenes)
        '#d68fe2',  # 3 - Agropecuária (Café)
        '#9932cc',  # 3 - Agropecuária (Citrus)
        '#9065d0',  # 3 - Agropecuária (Dendê)
        '#e6ccff',  # 3 - Agropecuária (Outras Lavouras Perenes)
        '#7a5900',  # 3 - Agropecuária (Silvicultura)
        '#d4271e',  # 4 - Área não Vegetada (Área Urbanizada)
        '#ffa07a',  # 4 - Área não Vegetada (Praia/Duna)
        '#9c0027',  # 4 - Área não Vegetada (Mineração)
        '#db4d4f',  # 4 - Área não Vegetada (Outras Áreas)
        '#2532e4',  # 5 - Corpo D'água (Rio/Lago/Oceano)
        '#091077'   # 5 - Corpo D'água (Aquicultura)
    ],
    'names': {
        0: "Não Observado",
        1: "Floresta",
        2: "Vegetação Herbácea",
        3: "Agropecuária",
        4: "Área não Vegetada",
        5: "Corpo D'água",
        6: "Não Observado"
    }
}

# Carregar imagem do MapBiomas Collection 9
mapbiomas_image = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')

# Função para reclassificar as bandas do MapBiomas
def reclassify_bands(image, codes, new_classes):
    remapped_bands = []  # Lista para armazenar as bandas reclassificadas
    for year in range(1985, 2024):  # Itera de 1985 a 2023
        original_band = f'classification_{year}'  # Nome da banda original
        # Reclassifica a banda usando os códigos e novas classes
        remapped_band = image.select(original_band).remap(codes, new_classes).rename(original_band)
        remapped_bands.append(remapped_band)  # Adiciona à lista
    return ee.Image.cat(remapped_bands)  # Concatena todas as bandas em uma única imagem

# Aplica a reclassificação
remapped_image = reclassify_bands(mapbiomas_image, CLASS_CONFIG['codes'], CLASS_CONFIG['new_classes'])

# Interface do usuário - Seleção de anos
years = list(range(1985, 2024))  # Lista de anos de 1985 a 2023
selected_years = st.multiselect('Selecione o(s) ano(s)', years, default=[2023])  # Widget multiseleção

# Seção para definição da área de estudo
geometry = None  # Inicializa a geometria como None
area_name = "Área Carregada"  # Nome padrão para a área

# Expander para as opções de definição de área
with st.expander('Defina a área de estudo', expanded=True):
    tab1, tab2, tab3 = st.tabs(["Selecionar Município", "Upload Shapefile", "Inserir GeoJSON"])
    
    with tab1:  # Aba para seleção de município
        if MUNICIPIOS_MA:  # Se municípios foram carregados
            municipio = st.selectbox(
                "Selecione um município do Maranhão", 
                options=sorted(MUNICIPIOS_MA.keys()),  # Ordena os municípios
                index=0  # Seleciona o primeiro por padrão
            )
        else:
            st.warning("Nenhum município carregado. Verifique o arquivo municipios_ma.geojson")
            municipio = None
    
    with tab2:  # Aba para upload de shapefile
        uploaded_files = st.file_uploader(
            "Faça upload dos arquivos do Shapefile (.shp, .dbf, .shx)",
            type=['shp', 'dbf', 'shx'],  # Tipos de arquivo aceitos
            accept_multiple_files=True  # Permite múltiplos arquivos
        )
    
    with tab3:  # Aba para inserção de GeoJSON manual
        geometry_input = st.text_area("Cole seu GeoJSON aqui")

# Processar entrada da área de estudo
if uploaded_files:  # Se arquivos foram enviados
    try:
        with tempfile.TemporaryDirectory() as temp_dir:  # Cria diretório temporário
            # Salva cada arquivo no diretório temporário
            for file in uploaded_files:
                file_path = os.path.join(temp_dir, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
            
            # Filtra apenas arquivos .shp
            shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
            if shp_files:
                # Lê o shapefile usando geopandas
                gdf = gpd.read_file(os.path.join(temp_dir, shp_files[0]))
                geojson = json.loads(gdf.to_json())  # Converte para GeoJSON
                # Cria geometria do Earth Engine
                geometry = ee.Geometry(geojson['features'][0]['geometry'])
                # Obtém o nome da área se existir
                area_name = geojson['features'][0]['properties'].get('name', 'Área Carregada')
                st.success("Shapefile carregado com sucesso!")
            else:
                st.error("Nenhum arquivo .shp encontrado nos arquivos enviados.")
    except Exception as e:
        st.error(f"Erro ao processar Shapefile: {str(e)}")

elif geometry_input.strip():  # Se foi inserido GeoJSON manualmente
    try:
        geo_data = json.loads(geometry_input)  # Tenta carregar o JSON
        if 'geometry' in geo_data:
            geometry = ee.Geometry(geo_data['geometry'])  # Cria geometria
        else:
            geometry = ee.Geometry(geo_data)  # Assume que é a geometria diretamente
        st.success("GeoJSON carregado com sucesso!")
    except Exception as e:
        st.error(f'Erro no GeoJSON: {str(e)}')

elif municipio and municipio in MUNICIPIOS_MA:  # Se município foi selecionado
    geometry = ee.Geometry(MUNICIPIOS_MA[municipio])  # Obtém geometria do município
    area_name = municipio  # Define o nome da área como o município
    st.success(f"Município {municipio} carregado com sucesso!")
    
# Visualização no mapa
m = geemap.Map(center=[-5, -45], zoom=6, plugin_Draw=True)  # Cria mapa centrado no MA

if geometry:  # Se há uma geometria definida
    study_area = ee.FeatureCollection([ee.Feature(geometry)])  # Cria feature collection
    m.centerObject(study_area, zoom=9)  # Centraliza o mapa na área
    # Adiciona camada da área de estudo
    m.addLayer(study_area, {'color': 'red', 'width': 2}, 'Área de estudo')
    remapped_image = remapped_image.clip(geometry)  # Recorta a imagem para a área
    
    # Adiciona camadas para cada ano selecionado
for year in selected_years:
    selected_band = f"classification_{year}"  # Nome da banda
    m.addLayer(
        remapped_image.select(selected_band),  # Seleciona a banda
        {
            'palette': CLASS_CONFIG['palette'],  # Usa a paleta definida
            'min': 0,  # Valor mínimo
            'max': 6   # Valor máximo
        },
        f"Classificação {year}"  # Nome da camada
    )

m.to_streamlit(height=600)  # Exibe o mapa no Streamlit

# Seção de estatísticas (apenas se houver geometria e anos selecionados)
if geometry and selected_years:
    st.subheader(f"📊 ESTATÍSTICAS DE ÁREA POR CLASSE - {area_name.upper()}")
    
    with st.spinner('Calculando estatísticas...'):  # Mostra spinner durante o cálculo
        stats_data = []  # Lista para armazenar os dados estatísticos
        for year in selected_years:  # Para cada ano selecionado
            band = remapped_image.select(f"classification_{year}")  # Seleciona a banda
            
            # Cria máscaras para todas as classes (0 a 6)
            class_masks = [band.eq(i).rename(f'class_{i}') for i in range(0, 7)]
            
            # Calcula áreas em metros quadrados e converte para km²
            areas = ee.Image.cat(*class_masks) \
               .multiply(ee.Image.pixelArea()) \
               .reduceRegion(
                   reducer=ee.Reducer.sum().repeat(7),
                   geometry=geometry,
                   scale=30,
                   maxPixels=1e13
               )
            
            try:
                areas_dict = areas.getInfo()  # Obtém os resultados
                
                if 'sum' in areas_dict:  # Verifica se há resultados
                    areas_list = areas_dict['sum']  # Obtém a lista de áreas
                    
                    for i in range(0, 7):  # Para cada classe
                        area_m2 = areas_list[i] if i < len(areas_list) else 0  # Área em m²
                        area_km2 = area_m2 / 1e6  # Converte para km²
                        
                        # Adiciona os dados à lista
                        stats_data.append({
                            "Ano": year,
                            "Classe": i,
                            "Nome da Classe": CLASS_CONFIG['names'].get(i, f"Classe {i}"),
                            "Área (km²)": round(area_km2, 2)  # Arredonda para 2 casas decimais
                        })
                else:
                    st.error(f"Formato inesperado de resultados para {year}")
                    
            except Exception as e:
                st.error(f"Erro ao processar {year}: {str(e)}")
                continue

    if not stats_data:  # Se não há dados
        st.warning("Nenhum dado encontrado para os parâmetros selecionados.")
        st.stop()  # Para a execução
    
    df = pd.DataFrame(stats_data)  # Cria DataFrame com os dados
    
# Agrega dados para evitar duplicatas (soma áreas por classe/ano)
    df_agg = df.groupby(['Ano', 'Nome da Classe'])['Área (km²)'].sum().reset_index()
    
    # GRÁFICO DE BARRAS EMPILHADAS HORIZONTAIS (100%)
    st.subheader("📊 DISTRIBUIÇÃO PERCENTUAL DAS CLASSES (GRÁFICO EMPILHADO)")
    
    # Prepara dados para o gráfico empilhado
    pivot_df = df_agg.pivot(index='Ano', columns='Nome da Classe', values='Área (km²)').fillna(0)
    
    # Calcula porcentagens
    pivot_percent = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100
    
    # Ordena as classes pela média de ocorrência
    class_order = pivot_percent.mean().sort_values(ascending=False).index
    pivot_percent = pivot_percent[class_order]
    
    # Define cores para as classes
    colors = [
        '#1f8d49',  # Floresta
        '#d6bc74',  # Vegetação Herbácea
        '#ffefc3',  # Agropecuária
        '#d4271e',  # Área não Vegetada
        '#2532e4',  # Corpo D'água
        '#ffffff'   # Não Observado
    ]
    
    # Cria figura do matplotlib
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plota gráfico de barras horizontais empilhadas
    pivot_percent.plot.barh(stacked=True, ax=ax, color=colors[:len(class_order)], width=0.8)
    
    # Configurações do gráfico
    ax.set_title(f'Distribuição Percentual das Classes de Cobertura - {area_name}', pad=20)
    ax.set_xlabel('Percentual (%)')
    ax.set_ylabel('Ano')
    ax.set_xlim(0, 100)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Move a legenda para fora do gráfico
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title='Classes')
    
    # Ajusta layout
    plt.tight_layout()
    
# Mostra o gráfico no Streamlit
    st.pyplot(fig)
    
    # GRÁFICO DE BARRAS IDÊNTICO AO SOLICITADO
    st.subheader(f"EVOLUÇÃO DAS CLASSES DE COBERTURA - {area_name.upper()}")
    
    # Define ordem e cores específicas
    custom_colors = {
        "Floresta": "#1f8d49",
        "Vegetação Herbácea": "#d6bc74",
        "Agropecuária": "#ffefc3", 
        "Área não Vegetada": "#d4271e",
        "Corpo D'água": "#2532e4",
        "Não Observado": "#ffffff"
    }
    
    # Cria gráfico de barras com Plotly
    bar_fig = px.bar(
        df_agg.sort_values("Ano"),  # Dados ordenados por ano
        x="Ano",  # Eixo X: anos
        y="Área (km²)",  # Eixo Y: áreas
        color="Nome da Classe",  # Cores por classe
        color_discrete_map=custom_colors,  # Mapa de cores personalizado
        barmode='group',  # Modo agrupado
        height=550  # Altura do gráfico
    )
    
# Personalização avançada do gráfico
    bar_fig.update_layout(
        font=dict(family="Arial", size=12, color="#333333"),  # Fonte
        plot_bgcolor='white',  # Cor de fundo do gráfico
        paper_bgcolor='white',  # Cor de fundo do papel
        xaxis=dict(
            title="Anos",
            showline=True,
            linecolor='black',
            tickmode='array',
            tickvals=selected_years,
            ticktext=[str(y) for y in selected_years]
        ),
        yaxis=dict(
            title="Área (km²)",
            showline=True,
            linecolor='black',
            gridcolor='rgba(200,200,200,0.3)',
            range=[0, df_agg['Área (km²)'].max()*1.2]  # Ajusta o range do eixo Y
        ),
        legend=dict(
            title="Classes",
            orientation="h",  # Legenda horizontal
            yanchor="bottom",
            y=-0.35,  # Posiciona abaixo do gráfico
            xanchor="center",
            x=0.5  # Centraliza
        ),
        hoverlabel=dict(  # Estilo do tooltip
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        )
    )
    
    # Estilo das barras
    bar_fig.update_traces(
        marker_line_width=1,
        marker_line_color='white',
        opacity=0.9,
        width=0.7,
        texttemplate='%{y:.1f}',  # Formato do texto
        textposition='outside'  # Posição do texto
    )
    
    st.plotly_chart(bar_fig, use_container_width=True)  # Exibe o gráfico
    
# Gráfico de Pizza Complementar
    st.subheader("🍕 DISTRIBUIÇÃO PERCENTUAL POR CLASSE")
    # Seleciona o ano para o gráfico de pizza
    selected_year = st.selectbox("Selecione o ano para análise:", sorted(selected_years, reverse=True), index=0)
    
    # Filtra dados para o ano selecionado
    year_df = df_agg[df_agg['Ano'] == selected_year]
    total_area = year_df['Área (km²)'].sum()  # Calcula área total
    year_df['Porcentagem'] = (year_df['Área (km²)'] / total_area) * 100  # Calcula porcentagens
    
    # Cria gráfico de pizza
    pie_fig = px.pie(
        year_df,
        names="Nome da Classe",  # Nomes das fatias
        values="Porcentagem",  # Valores das fatias
        title=f"Distribuição Percentual {selected_year}",  # Título
        color="Nome da Classe",  # Cores por classe
        color_discrete_map=custom_colors,  # Mapa de cores
        hole=0.4,  # Cria um donut
        height=500  # Altura
    )
    
    # Personaliza as fatias
    pie_fig.update_traces(
        textposition='inside',  # Texto dentro das fatias
        textinfo='percent+label',  # Mostra porcentagem e rótulo
        hovertemplate="<b>%{label}</b><br>%{percent:.1%}<br>Área: %{value:.2f} km²",  # Tooltip
        marker=dict(line=dict(color='white', width=1))  # Borda branca
    )
    
    st.plotly_chart(pie_fig, use_container_width=True)  # Exibe o gráfico
    
    # Tabela de Dados Completa
    st.subheader("📋 TABELA DE DADOS COMPLETA")
    # Cria tabela pivotada
    st.dataframe(
        df_agg.pivot(index='Ano', columns='Nome da Classe', values='Área (km²)')
        .style.format("{:.2f}")  # Formata números
        .set_properties(**{'background-color': '#f8f9fa', 'border': '1px solid #dee2e6'})  # Estilo
        .highlight_max(axis=0, color='#d4edda')  # Destaca máximos
        .highlight_min(axis=0, color='#f8d7da')  # Destaca mínimos
    )
    

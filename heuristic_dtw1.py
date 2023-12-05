import svgpathtools
from shapely.geometry import Polygon, box, Point
from shapely import unary_union
from shapely.affinity import translate, scale, rotate
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
import numpy as np
import matplotlib.pyplot as plt
import os
from itertools import chain

# Função para ler o SVG e extrair os contornos dos polígonos
def get_polygons_from_svg(svg_filepath):
    paths, attributes = svgpathtools.svg2paths(svg_filepath)
    polygons = []
    for path in paths:
        # Extrai os pontos do caminho
        points = [(seg.start.real, seg.start.imag) for seg in path] + [(path[0].start.real, path[0].start.imag)]

        # Verifica se há pelo menos 3 pontos distintos
        if len(set(points[:-1])) >= 3:  # O último ponto é uma repetição do primeiro
            polygons.append(Polygon(points))
    return polygons

# Função para converter um contorno de polígono em série temporal
def polygon_to_temporal_series(polygon):
    if not isinstance(polygon, Polygon):
        raise ValueError(f"Expected a Polygon, got {type(polygon)}")
    # Assumindo que polygon é um objeto da classe Polygon do Shapely
    x, y = polygon.exterior.coords.xy
    return list(zip(x, y))

# Função para aplicar DTW a dois contornos
def compare_contours_with_dtw(contour1, contour2):
    distance, path = fastdtw(contour1, contour2, dist=euclidean)
    return distance

# Desenhar os polígonos usando Matplotlib
def plot_polygons(polygons):
    for polygon in polygons:
        x, y = polygon.exterior.coords.xy
        plt.plot(x, y)

# Desenhar correspondências de DTW entre os contornos de dois polígonos
def plot_dtw_matching(contour1, contour2, path):
    # Desenhar a primeira forma
    x1, y1 = zip(*contour1)
    plt.plot(x1, y1, 'r')

    # Desenhar a segunda forma
    x2, y2 = zip(*contour2)
    plt.plot(x2, y2, 'g')

    # Traçar linhas entre pontos correspondentes
    for point1, point2 in path:
        plt.plot([contour1[point1][0], contour2[point2][0]], [contour1[point1][1], contour2[point2][1]], 'b', linestyle='--')


# Variáveis globais com as dimensões de uma folha A4 em milímetros e a distância mínima
a4_width, a4_height, min_distance = 210, 297, 5

# Funções get_polygons_from_svg e polygon_to_temporal_series já fornecidas em app2.py

# Função para ordenar as peças baseando-se na distância DTW
def order_pieces_by_dtw(polygons, temporal_series):
    dtw_results = {}
    for i, ts1 in enumerate(temporal_series):
        for j, ts2 in enumerate(temporal_series[i+1:], i+1):
            distance, _ = fastdtw(ts1, ts2, dist=euclidean)
            dtw_results[(i, j)] = distance
    # Ordena os pares de polígonos pela distância DTW crescente (menor distância primeiro)
    ordered_pairs = sorted(dtw_results, key=dtw_results.get)
    return ordered_pairs

# Função para encontrar a posição de encaixe no layout atual
def find_position(poly, current_layout, a4_width, a4_height, min_distance, angle_increment=90, line_thickness=0.5):
    """Encontra uma posição na folha A4 onde o polígono pode ser colocado,
    mantendo uma distância mínima entre as outras peças.

    Args:
        poly (shapely.geometry.Polygon): O polígono a ser colocado.
        current_layout (list): Lista atual das peças já empacotadas.
        a4_width (float): A largura da folha A4.
        a4_height (float): A altura da folha A4.
        min_distance (float): A distância mínima entre as peças.

    Returns:
        shapely.geometry.Polygon: O polígono transladado, ou None se não for encontrado encaixe.
    """
    # Cria um bounding box para a folha A4
    sheet_box = box(0, 0, a4_width, a4_height)

    # Corrige o polígono de entrada, se necessário
    if not poly.is_valid:
        poly = poly.buffer(0)

    # Considere a espessura da linha aplicando um buffer negativo nas peças antes de posicioná-las
    safety_buffer = poly.buffer(-line_thickness/2  if line_thickness < min_distance else 0)

    # Rotaciona o polígono em diferentes ângulos para encontrar uma posição sem colisão
    for angle in np.arange(0, 360, angle_increment):
        rotated_poly = rotate(safety_buffer, angle, origin='centroid')

        if not rotated_poly.is_valid:
            rotated_poly = rotated_poly.buffer(0)

        for y in np.arange(0, a4_height - rotated_poly.bounds[3], min_distance):
            for x in np.arange(0, a4_width - rotated_poly.bounds[2], min_distance):
                translated_poly = translate(rotated_poly, xoff=x, yoff=y)

                if not translated_poly.is_valid:
                    translated_poly = translated_poly.buffer(0)

                # Verifica colisões
                if translated_poly.within(sheet_box):
                    collision = False
                    for other_poly in current_layout:
                        if not other_poly.is_valid:
                            other_poly = other_poly.buffer(0)
                        if translated_poly.intersects(other_poly) and translated_poly.distance(other_poly) < min_distance:
                            collision = True
                            break
                    if not collision:
                        return translated_poly
    return None

# Função para plotar as peças
def plot_layout(layout):
    # Determina o número máximo de folhas que podem ser plotadas em uma única figura.
    max_sheets_per_fig = 1
    num_figures = (len(layout) + max_sheets_per_fig - 1) // max_sheets_per_fig

    for fig_idx in range(num_figures):
        fig, axs = plt.subplots(min(max_sheets_per_fig, len(layout) - fig_idx * max_sheets_per_fig), 1, figsize=(a4_width/25.4, a4_height/25.4 * max_sheets_per_fig))
        axs = np.array(axs).flatten()  # Garante que axs seja um array, mesmo com um único Axes
        for page_idx, ax in enumerate(axs):
            sheet_idx = fig_idx * max_sheets_per_fig + page_idx
            if sheet_idx >= len(layout):  # Se não houver folhas restantes para plotar, saia do loop
                break
            for poly in layout[sheet_idx]:
                x, y = poly.exterior.xy
                ax.plot(x, y)
            ax.set_xlim(0, a4_width)
            ax.set_ylim(0, a4_height)
            ax.set_aspect('equal')
            ax.set_title(f"Folha {sheet_idx + 1}")
            ax.invert_yaxis()  # Inverta o eixo y
        plt.show()

# Função para escalonar polígonos para determinadas unidades (por exemplo, polegadas)
def scale_polygon_to_inches(poly, scaling_factor=4):
    if not isinstance(poly, Polygon):
        raise ValueError(f"Expected a Polygon, got {type(poly)}")
    return scale(poly, xfact=1/scaling_factor, yfact=1/scaling_factor, origin=(0, 0))

def calculate_unfilled_area(layout, a4_width, a4_height):
    # A área total da folha A4
    a4_area = a4_width * a4_height
    unfilled_areas = []  # Lista para armazenar as áreas não preenchidas para cada folha
    for sheet in layout:
        # Combina as peças na folha para calcular a área coberta
        if sheet:  # Verifica se a folha não está vazia
            combined_polys = unary_union(sheet)
            filled_area = combined_polys.area
        else:
            # Se a folha estiver vazia, a área coberta é zero
            filled_area = 0
        # Calcula a área não preenchida subtraindo a área coberta da área total da folha
        unfilled_area = a4_area - filled_area
        unfilled_areas.append(unfilled_area)
    return unfilled_areas


# Principal fluxo de execução
def main(svg_folder_path):
    # Carrega todos os SVGs e converte em polígonos
    #polygons = [get_polygons_from_svg(os.path.join(svg_folder_path, f))
    #            for f in os.listdir(svg_folder_path) if f.lower().endswith('.svg')]
    #polygons = get_polygons_from_svg(svg_folder_path)
    #list_of_polygons_list= [poly.buffer(0) for poly in polygons if poly.is_valid]
    # Converte os polígonos em séries temporais
    #temporal_series = [polygon_to_temporal_series(poly) for poly in polygons]
    # Carrega todos os SVGs e converte em polígonos. Cada arquivo SVG pode ter vários polígonos.
    list_of_polygons_list = [get_polygons_from_svg(os.path.join(svg_folder_path, f))
                             for f in os.listdir(svg_folder_path)
                             if f.lower().endswith('.svg')]

    # Aplainar a lista de listas em uma única lista de polígonos
    polygons = list(chain.from_iterable(list_of_polygons_list))

    # Escalonar polígonos para polegadas
    for i in range(len(polygons)):
        polygons[i] = scale_polygon_to_inches(polygons[i])

    # Converte os polígonos em séries temporais
    #temporal_series = [polygon_to_temporal_series(polygon) for polygon in polygons]
    temporal_series = [polygon_to_temporal_series(poly) for poly in polygons]

    # Ordena as peças para a lógica de empacotamento baseado em DTW
    dtw_order = order_pieces_by_dtw(polygons, temporal_series)

    # Lista para manter o controle do layout das peças e folhas usadas
    placed_polygons = set()  # polígonos já colocados
    layout = [[]]  # Começa com uma folha A4 vazia

    # Cria uma nova folha A4 vazia
     # Cria uma nova folha A4 vazia
    #layout = [[]]

    # Empacota as peças na folha A4 de acordo com a distância DTW
    # Empacota as peças
    for pair in dtw_order:
        for index in pair:
            if index not in placed_polygons:  # Verifica se a peça ainda não foi colocada
                poly = polygons[index]
                position = find_position(poly, layout[-1], a4_width, a4_height, min_distance)

                # Se uma posição foi encontrada, adiciona ela à folha
                if position:
                    layout[-1].append(position)
                    placed_polygons.add(index)
                else:
                    # Se não achou um lugar na folha, cria uma nova folha e adiciona a peça lá
                    layout.append([poly])
                    placed_polygons.add(index)

    # Plotar o layout
    plot_layout(layout)
    print()
    # Calcule a área não preenchida para cada folha após o empacotamento
    unfilled_areas = calculate_unfilled_area(layout, a4_width, a4_height)
    for i, unfilled_area in enumerate(unfilled_areas, start=1):
        print(f"A área não preenchida na folha {i} é {unfilled_area} unidades quadradas.")


# Caminho para a pasta SVG
svg_folder_path = '/content/svg_harry'

# Executa o fluxo principal
main(svg_folder_path)
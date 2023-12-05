import svgpathtools
from shapely.geometry import Polygon, box, MultiPolygon
from shapely.affinity import translate, rotate, scale
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
import matplotlib.pyplot as plt

# Função para ler o SVG e extrair os contornos dos polígonos
def get_polygons_from_svg(svg_filepath):
    paths, attributes = svgpathtools.svg2paths(svg_filepath)
    polygons = []
    for path in paths:
        points = [(seg.start.real, seg.start.imag) for seg in path] + [(path[0].start.real, path[0].start.imag)]
        if len(set(points[:-1])) >= 3:  # Verifica por três pontos distintos
            polygons.append(Polygon(points))
    return polygons

# Função para converter um contorno de polígono em série temporal
def polygon_to_temporal_series(polygon):
    x, y = polygon.exterior.coords.xy
    return list(zip(x, y))

# Função para aplicar DTW a dois contornos
def compare_contours_with_dtw(contour1, contour2):
    distance, path = fastdtw(contour1, contour2, dist=euclidean)
    return distance, path

# Função para verificar colisões entre polígonos
def check_collision(poly_a, polys, min_distance=5):
    for poly_b in polys:
        if poly_a == poly_b: 
            continue
        if poly_a.intersects(poly_b) or poly_a.distance(poly_b) < min_distance:
            return True
    return False


# Função para garantir que todos os polígonos possam caber em uma folha A4
def verify_polygons_size(polygons, page_width=210, page_height=297):
    for poly in polygons:
        if poly.bounds[2] - poly.bounds[0] > page_width or poly.bounds[3] - poly.bounds[1] > page_height:
            return False
    return True


# Reposiciona o polígono na folha de tamanho A4
def reposition_polygon(poly, other_polys, page_width, page_height, min_distance):
    # Ajusta o polígono para ter o ponto inferior esquerdo em (0,0)
    poly = translate(poly, xoff=-poly.bounds[0], yoff=-poly.bounds[1])
    
    for y_offset in range(0, page_height - int(poly.bounds[3] - poly.bounds[1]), min_distance):
        for x_offset in range(0, page_width - int(poly.bounds[2] - poly.bounds[0]), min_distance):
            moved_poly = translate(poly, xoff=x_offset, yoff=-y_offset)
            if not check_collision(moved_poly, other_polys, min_distance):
                return moved_poly, True
    return poly, False  # Retorna o próprio polígono se não encontrar uma posição

# Função para posicionar os polígonos em folhas A4
def position_pieces_on_a4(polygons, page_width=210, page_height=297, min_distance=5):
    # Conferir se todos os polígonos cabem na folha A4
    if not verify_polygons_size(polygons, page_width, page_height):
        raise ValueError("Pelo menos um dos polígonos é muito grande para uma folha A4.")
    
    # Inicializa a primeira folha A4 e tenta posicionar todos os polígonos
    sheets = [[]]
    for poly in polygons:
        placed = False
        for sheet in sheets:
            positioned_poly, success = reposition_polygon(poly, sheet, page_width, page_height, min_distance)
            if success:
                sheet.append(positioned_poly)
                placed = True
                break
        if not placed:
            positioned_poly, success = reposition_polygon(poly, [], page_width, page_height, min_distance)
            if success:
                sheets.append([positioned_poly])
            else:
                raise ValueError("O polígono não pôde ser posicionado em uma nova folha A4 vazia.")  # Should not happen since we verified size before
    return sheets

# Função de plotagem revisada
def plot_sheets(sheets, page_width=210, page_height=297):
    for i, sheet in enumerate(sheets, start=1):
        plt.figure(figsize=(page_width / 25.4, page_height / 25.4))
        
        # Certificar-se de que a plotagem usa o canto inferior esquerdo como origem
        ax = plt.gca()
        ax.set_xlim(0, page_width)
        ax.set_ylim(0, page_height)
        ax.set_aspect('equal', adjustable='box')
        ax.invert_yaxis()  # Inverter eixo y para colocar a origem no canto inferior esquerdo
        
        for poly in sheet:
            # Se o polígono for um MultiPolygon, trate cada parte individualmente
            if isinstance(poly, MultiPolygon):
                for part in poly.geoms:
                    x, y = part.exterior.xy
                    plt.plot(x, y)
            else:
                x, y = poly.exterior.xy
                plt.plot(x, y)

        plt.title(f'Sheet {i}')
        plt.show()


# Função para redimensionar todos os polígonos de forma que eles fiquem contidos dentro das dimensões da folha A4
def resize_polygons_to_fit_a4(polygons, page_width=210, page_height=297, margin=10):
    max_width = max_height = 0
    # Calcula a maior largura e altura entre todos os polígonos
    for poly in polygons:
        poly_width, poly_height = poly.bounds[2] - poly.bounds[0], poly.bounds[3] - poly.bounds[1]
        max_width = max(max_width, poly_width)
        max_height = max(max_height, poly_height)

    # Determina o fator de escala com base no maior polígono e no tamanho da folha A4
    width_scale = (page_width - margin) / max_width
    height_scale = (page_height - margin) / max_height
    scale_factor = min(width_scale, height_scale)

    # Redimensiona todos os polígonos com o fator de escala calculado
    resized_polygons = [scale(poly, xfact=scale_factor, yfact=scale_factor, origin=(0, 0)) for poly in polygons]
    return resized_polygons

# -- Execução do processo de empacotamento --

# Altere o caminho para o arquivo SVG conforme necessário
svg_filepath = '/content/harry-potter.svg'

# No início do processo de empacotamento, logo após carregar os polígonos:
polygons = get_polygons_from_svg(svg_filepath)
resized_polygons = resize_polygons_to_fit_a4(polygons)  # Redimensionar polígonos

sheets = position_pieces_on_a4(resized_polygons) 

# Plote os polígonos posicionados em suas respectivas folhas
plot_sheets(sheets)

# -- Aqui você pode incluir a lógica de comparação de contornos com o DTW --
# Escolha dois polígonos para comparar e obtenha as séries temporais correspondentes
idx1, idx2 = 0, 1
contour1 = polygon_to_temporal_series(polygons[idx1])
contour2 = polygon_to_temporal_series(polygons[idx2])

# Compare os contornos com o DTW
distance, dtw_path = compare_contours_with_dtw(contour1, contour2)
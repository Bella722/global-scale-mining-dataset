# import geopandas as gpd
# import leafmap

# # 1. 读取 Shapefile
# shapefile_path = "global_mining_polygons_v1.shp"
# gdf = gpd.read_file(shapefile_path)

# # 2. 初始化地图
# m = leafmap.Map()
# m

# # 3. 遍历每个 Polygon
# for index, row in gdf.iterrows():
#     # 获取多边形中心点
#     centroid = row.geometry.centroid
#     lon, lat = centroid.x, centroid.y  # 中心经纬度

#     # 计算 BBOX（左右各 0.1°，上下各 0.1°）
#     bbox = [lon - 0.1, lat - 0.1, lon + 0.1, lat + 0.1]

#     # 输出文件名
#     image_name = f"polygon_{index}.tif"

#     # 下载影像（zoom 18 对应 ≈ 0.6m 分辨率，接近 0.5m）
#     leafmap.map_tiles_to_geotiff(
#         output=image_name, bbox=bbox, zoom=14, overwrite=True, source="SATELLITE"
#     )

#     print(f"下载完成: {image_name}")

# print("所有影像下载完成！")


# import geopandas as gpd
# import leafmap
# from pyproj import Transformer

# # 1. 读取 Shapefile
# shapefile_path = "global_mining_polygons_v1.shp"
# gdf = gpd.read_file(shapefile_path)

# # 2. 初始化地图
# m = leafmap.Map()
# m

# # 3. 经纬度 -> 米单位转换
# transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

# # 4. 遍历每个 Polygon
# for index, row in gdf.iterrows():
#     centroid = row.geometry.centroid
#     lon, lat = centroid.x, centroid.y  # 原始经纬度坐标

#     # 经纬度转换到米
#     x, y = transformer.transform(lon, lat)

#     # 定义窗口大小（单位：米）
#     size_m = 5000  # 5km
#     x_min, x_max = x - size_m, x + size_m
#     y_min, y_max = y - size_m, y + size_m

#     # 逆转换回 WGS84
#     transformer_back = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
#     lon_min, lat_min = transformer_back.transform(x_min, y_min)
#     lon_max, lat_max = transformer_back.transform(x_max, y_max)

#     # 生成最终 bbox
#     bbox = [lon_min, lat_min, lon_max, lat_max]

#     # 输出影像
#     image_name = f"polygon_{index}.tif"
#     leafmap.map_tiles_to_geotiff(
#         output=image_name, bbox=bbox, zoom=14, overwrite=True, source="SATELLITE"
#     )

#     print(f"下载完成: {image_name}")

# print("所有影像下载完成！")


import geopandas as gpd
import leafmap
import rasterio
import numpy as np
import cv2
import xml.etree.ElementTree as ET
from shapely.geometry import box, Polygon
from rasterio.transform import from_bounds
from pyproj import Transformer
import os

# 1. 读取 Shapefile，并转换到 EPSG:3857（确保与影像坐标系一致）
shapefile_path = "global_mining_polygons_v1.shp"
gdf = gpd.read_file(shapefile_path).to_crs("EPSG:3857")

# 2. 坐标转换工具（WGS84 <-> Web Mercator）
transformer_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
transformer_to_4326 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

# 3. 遍历每个 Polygon
for index, row in gdf.iterrows():
    centroid = row.geometry.centroid
    x, y = centroid.x, centroid.y  # 获取中心点的 Web Mercator 坐标
    
    # **获取 IQ03_CODE**
    iq03_code = str(row.get("ISO3_CODE", "unknown")).replace(" ", "_")  # 处理空值 & 空格

    # 4. 定义 bbox（单位：米）
    size_m = 5000  # 5km 半径
    x_min, x_max = x - size_m, x + size_m
    y_min, y_max = y - size_m, y + size_m

    # 5. 逆转换回 WGS84（用于下载影像）
    lon_min, lat_min = transformer_to_4326.transform(x_min, y_min)
    lon_max, lat_max = transformer_to_4326.transform(x_max, y_max)
    bbox = [lon_min, lat_min, lon_max, lat_max]

    # 6. **保存文件命名，加入 IQ03_CODE**
    image_name = f"{iq03_code}_polygon_{index}.tif"
    overlay_image_name = f"{iq03_code}_polygon_overlay_{index}.png"
    annotation_name = overlay_image_name.replace(".png", ".xml")

    # 7. 下载影像
    try:
        leafmap.map_tiles_to_geotiff(
            output=image_name, bbox=bbox, zoom=14, overwrite=True, source="SATELLITE"
        )
        print(f"下载完成: {image_name}")
    except Exception as e:
        print(f"下载失败: {image_name}")
        continue

    # 8. 读取影像
    with rasterio.open(image_name) as src:
        image = src.read([1, 2, 3])  # 读取 RGB 波段
        transform = src.transform  # 影像的地理变换矩阵
        width, height = src.width, src.height  # 影像尺寸

    # 9. 筛选 bbox 内的 Polygon（确保坐标匹配）
    bbox_geom = box(x_min, y_min, x_max, y_max)  # 以米为单位创建 bbox
    polygons_in_bbox = gdf[gdf.intersects(bbox_geom)]  # 选取 bbox 内的多边形

    # 10. **转换 Polygon 坐标到像素坐标**
    def transform_geometry_to_pixels(geom, transform):
        """ 将 EPSG:3857 坐标转换为影像的像素坐标 """
        if isinstance(geom, Polygon):
            return [~transform * (point[0], point[1]) for point in geom.exterior.coords]
        return []

    polygons_pixel_coords = [transform_geometry_to_pixels(geom, transform) for geom in polygons_in_bbox.geometry]

    # 11. 计算 BBox 并限制在图像范围内
    bboxes = []
    for poly in polygons_pixel_coords:
        if not poly:
            continue
        x_coords, y_coords = zip(*poly)
        x_min_px, x_max_px = int(max(0, min(x_coords))), int(min(width, max(x_coords)))
        y_min_px, y_max_px = int(max(0, min(y_coords))), int(min(height, max(y_coords)))

        bboxes.append((x_min_px, y_min_px, x_max_px, y_max_px))

    # 12. 将影像数据转换为 OpenCV 格式
    image_cv = np.transpose(image, (1, 2, 0))  # 转换为 HxWxC 格式
    image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGB2BGR)  # 转换为 BGR（OpenCV 默认格式）

    # 过滤出有效的 BBox 和对应的多边形
    valid_bboxes = []
    valid_polygons_pixel_coords = []

    for poly, bbox in zip(polygons_pixel_coords, bboxes):
        x1, y1, x2, y2 = bbox
        bbox_pixel_area = (x2 - x1) * (y2 - y1)

        if bbox_pixel_area > 8100:  # 只保留面积大于 5000 的 BBox
            valid_bboxes.append(bbox)
            valid_polygons_pixel_coords.append(poly)
        else:
            print(f"⚠️ 跳过 polygon {index}，BBox (像素) 面积过小: {bbox_pixel_area} px²")

    # 遍历有效的 BBox 和多边形进行绘制
    # for poly, bbox in zip(valid_polygons_pixel_coords, valid_bboxes):
    #     x1, y1, x2, y2 = bbox
    #     pts = np.array(poly, dtype=np.int32).reshape((-1, 1, 2))
    #     cv2.polylines(image_cv, [pts], isClosed=True, color=(0, 0, 255), thickness=2)  # 红色多边形
    #     cv2.rectangle(image_cv, (x1, y1), (x2, y2), (0, 255, 0), 2)  # 绿色 BBox


    # 14. 保存叠加影像
    cv2.imwrite(overlay_image_name, image_cv)
    print(f"已保存叠加多边形的影像: {overlay_image_name}")

    # 15. 生成 Pascal VOC 格式 XML 标注文件
    def create_pascal_voc_annotation(image_name, width, height, bboxes, label="kuangshan"):
        """ 生成 Pascal VOC XML 标注 """
        annotation = ET.Element("annotation")

        ET.SubElement(annotation, "folder").text = "images"
        ET.SubElement(annotation, "filename").text = image_name
        ET.SubElement(annotation, "path").text = image_name

        size = ET.SubElement(annotation, "size")
        ET.SubElement(size, "width").text = str(width)
        ET.SubElement(size, "height").text = str(height)
        ET.SubElement(size, "depth").text = "3"

        for bbox in bboxes:
            obj = ET.SubElement(annotation, "object")
            ET.SubElement(obj, "name").text = label
            ET.SubElement(obj, "pose").text = "Unspecified"
            ET.SubElement(obj, "truncated").text = "0"
            ET.SubElement(obj, "difficult").text = "0"

            bbox_xml = ET.SubElement(obj, "bndbox")
            ET.SubElement(bbox_xml, "xmin").text = str(bbox[0])
            ET.SubElement(bbox_xml, "ymin").text = str(bbox[1])
            ET.SubElement(bbox_xml, "xmax").text = str(bbox[2])
            ET.SubElement(bbox_xml, "ymax").text = str(bbox[3])

        tree = ET.ElementTree(annotation)
        tree.write(annotation_name)
        print(f"已保存 Pascal VOC 标注: {annotation_name}")

    # 16. 生成 XML 标注文件
    create_pascal_voc_annotation(overlay_image_name, width, height, valid_bboxes)
    src.close()  # 手动关闭文件
    try:
        os.remove(image_name)  # 删除原始影像
    except:
        print(f"⚠️ 无法删除原始影像: {image_name}")

print("所有影像下载、绘制和标注完成！")




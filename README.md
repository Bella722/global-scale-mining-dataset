# global-scale-mining-dataset
A global-scale data set of mining areas from Scientific Data

## 数据来源

[https://doi.pangaea.de/10.1594/PANGAEA.910894](https://doi.pangaea.de/10.1594/PANGAEA.910894)

原始数据是gpkg格式，我用代码转换为shp文件

```python
import geopandas as gpd

# 读取 GPKG
gdf = gpd.read_file("global_mining_polygons_v1.gpkg")

# 查看前 5 行
print(gdf.head())

# 保存为 Shapefile
gdf.to_file("global_mining_polygons_v1.shp")
```

然后shp内的每个polygon包含了地理信息以及其他内容，可以再结合leafmap直接下载tif影像甚至生成对应注释文件。
![image-20250311175017160](https://github.com/user-attachments/assets/6ea234f2-e120-457e-8c8d-99ee47676df4)
![image-20250311175037019](https://github.com/user-attachments/assets/25ae739b-9107-4fc7-bd86-3a02114b6a51)
可以看到具体有20000多的标注，也可以在谷歌地球上看到各个标注的分布
![image-20250311175339351](https://github.com/user-attachments/assets/6c23c0a0-1a43-48a5-8081-23c923cdc13c)
[聚焦第一个polygon可以看到具体标注内容](https://code.earthengine.google.com/dc90d9330d2b12558f1c975e41098aed)
![image-20250311175437932](https://github.com/user-attachments/assets/efd1f07f-0bb5-45e6-b28d-1e30ba11d38d)

## 制作数据集
运行downloadtif.py即可生成数据集
注：代码中会将多边形区域变换为正矩形以及一张图像上多个多边形的处理，并且设置过滤掉了个别太小的区域，但是还有一些标注有问题的区域需要手动清洗。

![image-20250311180025065](https://github.com/user-attachments/assets/522ae94a-a79b-4cb4-a00d-11761fee9cbe)

![image-20250311180102460](https://github.com/user-attachments/assets/6d289a1e-303c-4b3d-b38e-dc4aa9c9fbf5)

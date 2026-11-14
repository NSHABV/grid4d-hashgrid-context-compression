> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Full spatial sizes
| scene | xyz_parameters | xyz_bytes | RAW8_B | ZLIB8_B | FP32_to_RAW8_x | FP32_to_ZLIB8_x | RAW8_to_ZLIB8_x |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 12196216 | 48784864 | 12202580 | 2079708 | 3.997914 | 23.457555 | 5.867449 |
| hellwarrior | 12196216 | 48784864 | 12202579 | 1766604 | 3.997914 | 27.615054 | 6.907365 |
| hook | 12196216 | 48784864 | 12202579 | 1488870 | 3.997914 | 32.766369 | 8.195866 |
| jumpingjacks | 12196216 | 48784864 | 12202579 | 1917692 | 3.997914 | 25.439364 | 6.363159 |

| scene | xyz_MiB | RAW8_MiB | ZLIB8_MiB | RAW8_overhead_B |
| --- | --- | --- | --- | --- |
| bouncingballs | 46.524872 | 11.637287 | 1.983364 | 6364 |
| hellwarrior | 46.524872 | 11.637286 | 1.684765 | 6363 |
| hook | 46.524872 | 11.637286 | 1.419897 | 6363 |
| jumpingjacks | 46.524872 | 11.637286 | 1.828854 | 6363 |

Parameter accounting:
| scene | xyz_share_deformation | xyz_share_full_scene | full_scene_parameters | other_parameter_bytes | model_only_checkpoint_bytes |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | 92.221278 | 50.390318 | 24203491 | 48029100 | 96836836 |
| hellwarrior | 92.221278 | 76.500202 | 15942724 | 14986032 | 63796580 |
| hook | 92.221278 | 47.857168 | 25484617 | 53153604 | 101960868 |
| jumpingjacks | 92.221278 | 57.602963 | 21172897 | 35906724 | 84715876 |

Число deformation parameters = spatial+temporal+MLP, buffers исключены. Full-scene parameters дополнительно включает обучаемые поля Gaussian PLY (xyz,SH,opacity,scale,rotation), исключая производные normals. Все обучаемые tensors здесьFP32. Original deform.pth — tuple(grid,network), без optimizer; файл не содержит Gaussian PLY. Полный model-only tensor archive включает эти Gaussian fields и grid buffers, но не optimizer: это диагностический PyTorch архив, не новая standalone scene. Размеры файлов и tensor bytes различаются из-за сериализации.
| scene | original_deform_checkpoint_bytes | original_Gaussian_PLY_bytes | deformation_parameter_bytes | full_scene_parameter_bytes | model_only_checkpoint_bytes |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | 52908789 | 46148627 | 52899792 | 96813964 | 96836836 |
| hellwarrior | 52908789 | 11425402 | 52899792 | 63770896 | 63796580 |
| hook | 52908789 | 51533699 | 52899792 | 101938468 | 101960868 |
| jumpingjacks | 52908789 | 33409859 | 52899792 | 84691588 | 84715876 |


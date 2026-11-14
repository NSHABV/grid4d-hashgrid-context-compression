// Diagnostic only. Header is an exact byte slice of pinned upstream CUDA helpers.
#include <torch/extension.h>
#include <ATen/cuda/CUDAContext.h>
#include <cuda_runtime.h>
#include "upstream_index.inc"

__global__ void index_probe(const int* v,const int* r,int rows,int n,int* out){
 int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;
 uint32_t p[3],res[3];for(int d=0;d<3;d++){p[d]=v[3*i+d];res[d]=r[d];}
 out[i]=get_grid_index<3,2>(0,rows,res,p)/2;
}
__global__ void scales_probe(const float* q,const float* base,int levels,float* scale,int* res){
 int l=blockIdx.x*blockDim.x+threadIdx.x;if(l>=levels)return;
 for(int d=0;d<3;d++){float s=exp2f(l*q[d])*base[d]-1.0f;scale[l*3+d]=s;res[l*3+d]=(uint32_t)ceil(s)+1;}
}
at::Tensor indices(at::Tensor v,at::Tensor r,int rows){
 TORCH_CHECK(v.is_cuda()&&r.is_cuda()&&v.is_contiguous()&&r.is_contiguous());
 TORCH_CHECK(v.scalar_type()==at::kInt&&r.scalar_type()==at::kInt&&v.dim()==2&&v.size(1)==3&&r.numel()==3&&rows>0);
 auto out=at::empty({v.size(0)},v.options());
 index_probe<<<(v.size(0)+255)/256,256,0,at::cuda::getCurrentCUDAStream()>>>(v.data_ptr<int>(),r.data_ptr<int>(),rows,v.size(0),out.data_ptr<int>());return out;
}
std::vector<at::Tensor> scales(at::Tensor q,at::Tensor base,int levels){
 TORCH_CHECK(q.is_cuda()&&base.is_cuda()&&q.numel()==3&&base.numel()==3&&q.scalar_type()==at::kFloat&&base.scalar_type()==at::kFloat);
 auto s=at::empty({levels,3},q.options());auto r=at::empty({levels,3},q.options().dtype(at::kInt));
 scales_probe<<<(levels+255)/256,256,0,at::cuda::getCurrentCUDAStream()>>>(q.data_ptr<float>(),base.data_ptr<float>(),levels,s.data_ptr<float>(),r.data_ptr<int>());return {s,r};
}
PYBIND11_MODULE(TORCH_EXTENSION_NAME,m){m.def("indices",&indices);m.def("scales",&scales);}

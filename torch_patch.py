import sys
import types
import importlib.machinery

# ---- Create fake torch module ----
fake_torch = types.ModuleType("torch")
fake_torch.__spec__ = importlib.machinery.ModuleSpec("torch", loader=None)

# ---- Fake dtype constants ----
fake_torch.int8 = "int8"
fake_torch.int16 = "int16"
fake_torch.int32 = "int32"
fake_torch.int64 = "int64"
fake_torch.float16 = "float16"
fake_torch.float32 = "float32"
fake_torch.float64 = "float64"
fake_torch.bfloat16 = "bfloat16"
fake_torch.bool = "bool"

# ---- Fake submodules ----
nn_module = types.ModuleType("torch.nn")
nn_module.Module = object  # minimal placeholder for nn.Module
fake_torch.nn = nn_module

cuda_module = types.ModuleType("torch.cuda")
cuda_module.is_available = lambda: False
fake_torch.cuda = cuda_module

# ---- Minimal fake API ----
fake_torch.__dict__.update({
    "__version__": "0.0",
    "device": lambda *a, **kw: "cpu",
    "Tensor": object,
    "dtype": type("dtype", (), {})(),
    "nn": nn_module,
    "cuda": cuda_module,
})

# ---- Register fake modules globally ----
sys.modules["torch"] = fake_torch
sys.modules["torch.nn"] = nn_module
sys.modules["torch.cuda"] = cuda_module

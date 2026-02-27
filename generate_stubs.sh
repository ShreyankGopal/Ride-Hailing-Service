#!/bin/bash

# Path to your proto files directory
PROTO_DIR="Proto"

# Output folder for all generated stubs
OUT_DIR="Generated_Stubs"

echo "Generating Python gRPC stubs..."
echo "Proto source: $PROTO_DIR"
echo "Output base:  $OUT_DIR"
echo ""

# Loop through every .proto file in the directory
for proto_file in "$PROTO_DIR"/matching.proto; do
    
    # Check if file exists (prevents errors if directory is empty)
    [ -e "$proto_file" ] || continue

    # 1. Get the filename (e.g., "xyz.proto")
    filename=$(basename -- "$proto_file")
    
    # 2. Get the name without extension (e.g., "xyz")
    name="${filename%.*}"
    
    # 3. Define the specific target directory (Generated_Stubs/xyz/)
    TARGET_SUBDIR="$OUT_DIR/$name"
    
    # 4. Create that directory
    mkdir -p "$TARGET_SUBDIR"

    echo "• Processing $filename -> $TARGET_SUBDIR/"

    # 5. Generate stubs targeting that specific subdirectory
    python -m grpc_tools.protoc \
        -I="$PROTO_DIR" \
        --python_out="$TARGET_SUBDIR" \
        --grpc_python_out="$TARGET_SUBDIR" \
        "$proto_file"

    # Check for errors immediately
    if [ $? -ne 0 ]; then
        echo "❌ Failed to generate stubs for $filename"
        exit 1
    fi
done

echo ""
echo "✔ All stubs successfully generated."
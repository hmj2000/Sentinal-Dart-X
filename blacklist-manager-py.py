import os
import argparse
import uuid
from blacklist import BlacklistDatabase

def add_face_from_image(blacklist_db, image_path, name=None, notes=None):
    """Add a face from an image file to the blacklist"""
    face_encoding = blacklist_db.encode_face_from_image(image_path)
    
    if face_encoding is None:
        print(f"在{image_path}中找不到人脸")
        return False
    
    # Create metadata
    metadata = {}
    if name:
        metadata['name'] = name
    if notes:
        metadata['notes'] = notes
    
    # Generate unique ID for the face
    face_id = str(uuid.uuid4())
    
    # Add to blacklist
    success = blacklist_db.add_face(face_id, face_encoding, metadata)
    
    if success:
        print(f"已添加人脸ID: {face_id}到黑名单" + (f" (姓名: {name})" if name else ""))
    else:
        print("添加人脸到黑名单失败")
    
    return success

def remove_face(blacklist_db, face_id):
    """Remove a face from the blacklist by ID"""
    success = blacklist_db.remove_face(face_id)
    
    if success:
        print(f"已从黑名单中移除人脸ID: {face_id}")
    else:
        print(f"在黑名单中找不到人脸ID: {face_id}")
    
    return success

def list_faces(blacklist_db):
    """List all faces in the blacklist"""
    faces = blacklist_db.get_all_faces()
    
    if not faces:
        print("黑名单为空")
        return
    
    print(f"在黑名单中找到{len(faces)}个人脸:")
    for face_id, data in faces.items():
        metadata = data['metadata']
        name = metadata.get('name', '未知')
        notes = metadata.get('notes', '')
        added_on = metadata.get('added_on', '未知时间')
        print(f"ID: {face_id} | 姓名: {name} | 添加时间: {added_on}" + (f" | 备注: {notes}" if notes else ""))

def main():
    parser = argparse.ArgumentParser(description='管理人脸识别黑名单数据库')
    subparsers = parser.add_subparsers(dest='command', help='要执行的命令')
    
    # Add face parser
    add_parser = subparsers.add_parser('add', help='添加人脸到黑名单')
    add_parser.add_argument('image_path', help='图像文件路径')
    add_parser.add_argument('--name', help='人物姓名')
    add_parser.add_argument('--notes', help='额外备注')
    
    # Remove face parser
    remove_parser = subparsers.add_parser('remove', help='从黑名单移除人脸')
    remove_parser.add_argument('face_id', help='要移除的人脸ID')
    
    # List faces parser
    list_parser = subparsers.add_parser('list', help='列出黑名单中的所有人脸')
    
    args = parser.parse_args()
    
    # Initialize blacklist database
    blacklist_db = BlacklistDatabase()
    
    if args.command == 'add':
        add_face_from_image(blacklist_db, args.image_path, args.name, args.notes)
    elif args.command == 'remove':
        remove_face(blacklist_db, args.face_id)
    elif args.command == 'list':
        list_faces(blacklist_db)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

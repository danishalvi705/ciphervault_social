from PIL import Image, ImageDraw

def create_card(signal_data, output_path="temp_card.png"):
    # Load your template (800x1200)
    frame = Image.open("glass_template.png").convert("RGBA")
    final_card = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    final_card.paste(frame, (0, 0), frame)
    
    draw = ImageDraw.Draw(final_card)
    
    # Coordinates mapping (X, Y)
    # Adjust these to fit inside your Neon Glass boxes
    draw.text((100, 200), f"{signal_data.get('symbol', 'BTC/USDT')}", fill="white")
    draw.text((100, 350), f"ENTRY: {signal_data.get('entry', '0.00')}", fill="green")
    draw.text((100, 450), f"TP1: {signal_data.get('tp1', '0.00')}", fill="white")
    draw.text((100, 550), f"TP2: {signal_data.get('tp2', '0.00')}", fill="white")
    draw.text((100, 650), f"TP3: {signal_data.get('tp3', '0.00')}", fill="white")
    draw.text((100, 750), f"SL: {signal_data.get('sl', '0.00')}", fill="red")
    
    # Bottom Row (Grade, Score, R:R)
    draw.text((150, 950), f"GRADE: {signal_data.get('grade', 'A')}", fill="white")
    draw.text((350, 950), f"SCORE: {signal_data.get('score', '8.5/10')}", fill="white")
    draw.text((550, 950), f"R:R: {signal_data.get('rr', '3.0x')}", fill="white")
    
    final_card.save(output_path, "PNG")

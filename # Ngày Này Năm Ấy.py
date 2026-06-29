# Ngày Này Năm Ấy
# Nếu muốn thêm nhạc khi chạy code thì bạn hãy tải nhạc về và đặt tên thành music.mp3
# đặt nó cùng thư mục với tệp này và chạy mã sẽ có nhạc khi chạy
# Open pygame cài đặt pip nhập CMD (nếu chưa cài đặt)
nhập  sys , io ,  os ,  time ,  threading
_stdout , _stderr =  sys . stdout ,  sys . stderr
sys.stdout , sys.stderr = io.StringIO ( ) , io.StringIO ( )​​​​​​  
nhập khẩu pygame
sys . stdout ,  sys . stderr  = _stdout , _stderr
 
 
pygame.mixer.init ( )​​​
 
# Mã màu ANSI
lớp Mau:
    ĐẶT LẠI =  ' \0 33[0m'
    ĐẬM =  ' \0 33[1m'
    HONG_NHAT =  ' \0 33[38;2;255;150;170m'  
    XANH_NHAT =  ' \0 33[38;2;120;200;230m'  
    XANH_LA_NHAT =  ' \0 33[38;2;120;230;120m'  
    VANG_NHAT =  ' \0 33[38;2;255;230;150m'  
    TIM_NHAT =  ' \0 33[38;2;200;120;200m'  
    OAI_HUONG =  ' \0 33[38;2;200;200;250m'  
    BAC_HA =  ' \0 33[38;2;150;240;180m'  
    XANH_LUC_NHAT =  ' \0 33[38;2;180;255;255m'  
 
def xoa_man_hinh ( ) :
    os.system ( 'cls' nếu os.name == ' nt' nếu không thì ' clear ' )      
 
def hieu_ung_chu ( lyrics_list , start_time = None , char_speed = None ) :
    nếu start_time là  None :
        start_time =  [ 0 ] * len ( danh sách lời bài hát )
    nếu char_speed là  None :
        char_speed =  [ 0,08 ] * len ( danh sách lời bài hát )
 
    bat_dau =  thời gian . thời gian ( )
    màu cơ sở =  [
        Mậu. XANH_NHAT , Mau. TIM_NHAT , Mau. OAI_HƯƠNG ,
        Mậu. BAC_HA , Mau. HONG_NHAT , Mau. XANH_LA_NHAT ,
        Mậu. XANH_LUC_NHAT , Mau. VANG_NHAT
    ]
 
    xoa_man_hinh ( )
 
    đối với idx , dòng trong  enumerate ( lyrics_list ) :
        trong khi  thời gian . time ( ) -bat_dau < start_time [ idx ] :
            thời gian . ngủ ( 0,01 )
 
        màu_hiện_tại = màu_cơ_bản [ idx % len ( màu_cơ_bản ) ]
 
        dòng_hiện_tại =  ""
        đối với i , char trong  enumerate ( dòng ) :
            # Giữ hiệu ứng mờ dần nhưng màu nền đậm hơn
            sóng  =  ( i / len ( dòng ) ) * 0,8 + 0,2
            nếu current_color == Mau. XANH_NHAT : r , g , b = int ( 120 * wave ) , int ( 200 * wave ) , int ( 230 * wave )
            elif current_color == Mau. TIM_NHAT : r , g , b = int ( 200 * wave ) , int ( 120 * wave ) , int ( 200 * wave )
            elif current_color == Mau. OAI_HUONG : r , g , b = int ( 200 * wave ) , int ( 200 * wave ) , int ( 250 * wave )
            elif current_color == Mau. BAC_HA : r , g , b = int ( 150 * wave ) , int ( 240 * wave ) , int ( 180 * wave )
            elif current_color == Mau. HONG_NHAT : r , g , b = int ( 255 * wave ) , int ( 150 * wave ) , int ( 170 * wave )
            elif current_color == Mau. XANH_LA_NHAT : r , g , b = int ( 120 * sóng ) , int ( 230 * sóng ) , int ( 120 * sóng )
            elif current_color == Mau. XANH_LUC_NHAT : r , g , b = int ( 180 * wave ) , int ( 255 * wave ) , int ( 255 * wave )
            nếu không : r , g , b = int ( 255 * wave ) , int ( 230 * wave ) , int ( 150 * wave )
 
            dòng_hiện_tại + = f " \0 33[38;2;{r};{g};{b}m{char}{Mau.RESET}"
            sys . stdout . write ( f " \r {dòng_hiện_tại}" )
            sys . stdout . flush ( )
            thời gian . ngủ ( char_speed [ idx ] )
 
        in ( )
 
# HÀM NÀY DÙNG ĐỂ PHÁT NHẠC
định nghĩa play_music ( ) :
    """Phát nhạc nền nếu file music.mp3 tồn tại"""
    nếu  os . con đường . tồn tại ( "music.mp3" ) :   # Dòng này kiểm tra file tồn tại không
        pygame.mixer.music.load ( " music.mp3 " )​​​
        pygame.mixer.music.play ( )​​​​​
 
định nghĩa show_lyrics ( ) :
 
    # lời bài hát
    danh sách lời bài hát =  [
        "Em đã xa anh mất rồi người ơi" ,
        "Lời hứa gió bay hết rồi người ơi" ,
        "Ta đến bên nhau để dạy nhau" ,
        "Yêu một ai thật chân thành" ,
        "Nhưng chân thành dành cho người sau" ,
        "Mưa nắng giông gió trời em ơi" ,
        "Thời gian cũng sẽ chữa lành anh thôi" ,
        "Người đã buông tay rồi" ,
        "Gửi cuối bao đôi lời" ,
        " \" Lòng chơi vơi \" "
    ]
 
 
    thời gian bắt đầu =  [ 0 ,  3.0 ,  7.0 ,  10.0 ,  12.0 ,  14.0 ,  17.0 ,  22.0 ,  24.0 ,  25.0 ] 
    tốc độ ký tự =  [ 0,1 ,  0,1 ,  0,1 ,  0,07 ,  0,05 ,  0,07 ,  0,1 ,  0,05 ,  0,06 ,  0,05 ]
 
    # DÒNG NÀY TẠO LUỒNG PHỤ ĐỂ PHÁT NHẠC (chạy tăng)
    luồng . Luồng ( mục tiêu = play_music , daemon = True ) . bắt đầu ( )
    global_start =  thời gian . thời gian ( )
 
    hieu_ung_chu ( lyrics_list , start_time , char_speed )
 
    đã trôi qua =  thời gian . time ( ) - global_start
    nếu trôi qua <  30 :
        thời gian . giấc ngủ ( 30 - đã trôi qua )
 
    # DÒNG NÀY DỪNG NHẠC KHI KẾT THÚC
    pygame.mixer.music.stop ( )​​​​​
 
nếu __name__ ==  "__main__" :
    hiển thị_lời_hát ( )
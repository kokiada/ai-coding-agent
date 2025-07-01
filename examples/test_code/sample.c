/**
 * サンプルC言語ファイル
 * 意図的にレビュー問題を含む
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// グローバル変数（推奨されない）
int g_counter = 0;

// 危険な関数を使用した例
void unsafe_string_copy(char* dest, const char* src) {
    strcpy(dest, src);  // バッファオーバーフローの危険性
}

// メモリリークの例
char* create_buffer(int size) {
    char* buffer = malloc(size);
    // NULLチェックなし
    strcpy(buffer, "Hello");  // さらに危険
    return buffer;
    // freeされていない
}

// 複雑すぎる関数の例
int complex_function(int a, int b, int c, int d) {
    int result = 0;
    
    if (a > 0) {
        if (b > 0) {
            if (c > 0) {
                if (d > 0) {
                    for (int i = 0; i < a; i++) {
                        for (int j = 0; j < b; j++) {
                            if (i * j > 100) {
                                result += i * j;
                            } else {
                                result -= i + j;
                            }
                        }
                    }
                } else {
                    result = a * b * c;
                }
            } else {
                result = a * b;
            }
        } else {
            result = a;
        }
    }
    
    return result;
}

// メモリ管理の問題がある関数
void memory_problem_example() {
    char* ptr1 = malloc(100);
    char* ptr2 = malloc(200);
    char* ptr3 = malloc(300);
    
    // ptr1とptr3のみfree、ptr2がリーク
    free(ptr1);
    free(ptr3);
    
    // ダブルフリーの危険性
    free(ptr3);  
}

// マジックナンバーの例
int calculate_area(int width, int height) {
    if (width > 1920 || height > 1080) {  // マジックナンバー
        return -1;
    }
    return width * height;
}

int main() {
    char buffer[10];  // 小さなバッファ
    char input[100] = "This is a very long string that will overflow the buffer";
    
    // 危険な操作
    unsafe_string_copy(buffer, input);
    
    // メモリリーク
    char* leaked_memory = create_buffer(1000);
    
    // 複雑な関数呼び出し
    int result = complex_function(5, 10, 15, 20);
    
    printf("Result: %d\n", result);
    
    return 0;  // leaked_memoryがfreeされていない
}
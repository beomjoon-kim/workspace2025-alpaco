const readline = require("readline");

// readline 모듈을 이용해서 입력 interface 준비
const input = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// 콜백함수: 먼저 함수의 모든 실행이 끝나면 후속으로 실행하는 함수.
// question()이 키 입력 받는 함수, 콜백함수 실행.
input.question("당신의 이름은? ", function(answer) {
  console.log("안녕하세요, " + answer + "님!");
  rl.close(); // 입력 종료
});

// streaming.js - 배경 스트리밍용 JavaScript (향상된 로깅)
console.log('🎥 배경 스트리밍 시스템 로드됨');

class BackgroundStreaming {
    constructor() {
        // WebSocket 설정
        this.signalingUrl = 'ws://172.18.73.63:3001';
        this.roomId = 'factory-screen';
        
        // 상태 변수
        this.webrtcSocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.isStreaming = false;
        this.currentVideoElement = null;
        
        // 성능 통계
        this.frameCount = 0;
        this.startTime = Date.now();
        this.lastFrameTime = 0;
        this.errorCount = 0;
        
        // DOM 요소
        this.streamBackground = null;
        this.streamStatus = null;
        this.loadingIndicator = null;
        
        // 초기화
        this.init();
    }
    
    init() {
        console.log('🔧 배경 스트리밍 시스템 초기화');
        this.addLog('스트리밍 시스템 초기화', 'info');
        
        // DOM 로드 대기
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupDOM());
        } else {
            this.setupDOM();
        }
    }
    
    setupDOM() {
        console.log('🌐 DOM 설정');
        this.addLog('DOM 설정 완료', 'success');
        
        // DOM 요소 가져오기
        this.streamBackground = document.getElementById('stream-background');
        this.streamStatus = document.getElementById('stream-status');
        this.loadingIndicator = document.getElementById('loading-indicator');
        
        if (!this.streamBackground) {
            this.addLog('❌ stream-background 요소를 찾을 수 없음', 'error');
            console.error('❌ stream-background 요소를 찾을 수 없습니다');
            return;
        }
        
        // 이벤트 리스너 설정
        this.setupEventListeners();
        
        // 스트리밍 시작 (지연)
        setTimeout(() => this.connectToSignalingServer(), 2000);
    }
    
    setupEventListeners() {
        console.log('⌨️ 이벤트 리스너 설정');
        this.addLog('키보드 단축키 설정됨', 'info');
        
        document.addEventListener('keydown', (event) => {
            switch(event.key) {
                case 'F5':
                    event.preventDefault();
                    this.manualReconnect();
                    break;
                case 'F12': // F12로 스트리밍 토글
                    event.preventDefault();
                    this.toggleStreaming();
                    break;
            }
        });
        
        // 페이지 언로드 시 정리
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
        
        // 네트워크 상태 모니터링
        window.addEventListener('online', () => {
            this.addLog('네트워크 연결 복구됨', 'success');
            this.connectToSignalingServer();
        });
        
        window.addEventListener('offline', () => {
            this.addLog('네트워크 연결 끊어짐', 'error');
        });
    }
    
    addLog(message, type = 'info') {
        // 콘솔 로그
        const timestamp = new Date().toLocaleTimeString();
        console.log(`[${timestamp}] ${message}`);
        
        // 부모 창의 로그 함수 호출 (iframe이 아닌 경우)
        try {
            if (window.parent && window.parent.addStreamingLog) {
                window.parent.addStreamingLog(message, type);
            } else if (window.addStreamingLog) {
                window.addStreamingLog(message, type);
            }
        } catch (e) {
            // 무시 (크로스 오리진 이슈)
        }
    }
    
    updateStatus(message, type = 'info') {
        try {
            if (this.streamStatus) {
                this.streamStatus.textContent = message;
                this.streamStatus.className = `status-${type}`;
            }
            
            const emoji = {
                'info': '🔄',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌'
            };
            
            this.addLog(`${emoji[type] || '📊'} ${message}`, type);
        } catch (error) {
            console.error('❌ 상태 업데이트 오류:', error);
        }
    }
    
    connectToSignalingServer() {
        const attemptText = `(${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`;
        console.log(`📡 시그널링 서버 연결 시도: ${this.signalingUrl} ${attemptText}`);
        this.updateStatus(`🔄 연결 중... ${attemptText}`, 'info');
        
        try {
            // 기존 연결 정리
            if (this.webrtcSocket) {
                this.webrtcSocket.close();
            }
            
            // 새 WebSocket 연결
            this.webrtcSocket = new WebSocket(this.signalingUrl);
            
            // 연결 타임아웃 설정
            const connectionTimeout = setTimeout(() => {
                if (this.webrtcSocket.readyState === WebSocket.CONNECTING) {
                    this.addLog('연결 시간 초과', 'error');
                    this.webrtcSocket.close();
                }
            }, 10000); // 10초 타임아웃
            
            this.webrtcSocket.onopen = () => {
                clearTimeout(connectionTimeout);
                this.onWebSocketOpen();
            };
            this.webrtcSocket.onmessage = (event) => this.onWebSocketMessage(event);
            this.webrtcSocket.onclose = (event) => this.onWebSocketClose(event);
            this.webrtcSocket.onerror = (error) => this.onWebSocketError(error);
            
        } catch (error) {
            console.error('❌ WebSocket 생성 오류:', error);
            this.updateStatus('❌ 연결 실패', 'error');
            this.addLog(`WebSocket 생성 오류: ${error.message}`, 'error');
            this.scheduleReconnect();
        }
    }
    
    onWebSocketOpen() {
        console.log('✅ 시그널링 서버 연결 성공');
        this.updateStatus('✅ 연결됨', 'success');
        this.reconnectAttempts = 0;
        this.addLog('시그널링 서버 연결 성공', 'success');
        
        // 뷰어로 방 참가
        const joinMessage = {
            type: 'join-room',
            roomId: this.roomId,
            role: 'viewer'
        };
        
        try {
            this.webrtcSocket.send(JSON.stringify(joinMessage));
            console.log(`📺 ${this.roomId} 방에 뷰어로 참가`);
            this.addLog(`방 참가: ${this.roomId}`, 'info');
        } catch (error) {
            console.error('❌ 방 참가 메시지 전송 오류:', error);
            this.addLog(`방 참가 실패: ${error.message}`, 'error');
        }
    }
    
    onWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        } catch (error) {
            console.error('❌ 메시지 파싱 오류:', error);
            this.addLog(`메시지 파싱 오류: ${error.message}`, 'error');
            this.errorCount++;
        }
    }
    
    onWebSocketClose(event) {
        const reason = this.getCloseReason(event.code);
        console.log(`❌ WebSocket 연결 종료. Code: ${event.code}, Reason: ${reason}`);
        this.addLog(`연결 종료: ${reason} (${event.code})`, 'error');
        
        this.isStreaming = false;
        this.clearStream();
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.updateStatus(`🔄 재연결 중...`, 'warning');
            this.scheduleReconnect();
        } else {
            this.updateStatus('❌ 연결 실패', 'error');
            this.addLog('최대 재연결 시도 횟수 초과', 'error');
        }
    }
    
    onWebSocketError(error) {
        console.error('❌ WebSocket 오류:', error);
        this.updateStatus('❌ 연결 오류', 'error');
        this.addLog(`WebSocket 오류: ${error.message || '알 수 없는 오류'}`, 'error');
        this.errorCount++;
    }
    
    getCloseReason(code) {
        const reasons = {
            1000: '정상 종료',
            1001: '서버 종료',
            1002: '프로토콜 오류',
            1003: '지원하지 않는 데이터',
            1006: '비정상 종료',
            1007: '잘못된 데이터',
            1008: '정책 위반',
            1009: '메시지 크기 초과',
            1011: '서버 오류'
        };
        return reasons[code] || `알 수 없는 오류 (${code})`;
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'streamer-joined':
                console.log('🎥 스트리머 연결됨');
                this.updateStatus('🎥 스트리머 연결됨', 'success');
                this.addLog('스트리머가 연결되었습니다', 'success');
                break;
                
            case 'streamer-left':
                console.log('📴 스트리머 연결 해제됨');
                this.updateStatus('📴 스트리머 해제됨', 'warning');
                this.addLog('스트리머 연결이 해제되었습니다', 'warning');
                this.isStreaming = false;
                this.clearStream();
                break;
                
            case 'screen-share-status':
                if (data.streaming) {
                    console.log('🖥️ 화면 공유 시작됨');
                    this.updateStatus('🖥️ 스트리밍 중', 'success');
                    this.addLog('화면 공유가 시작되었습니다', 'success');
                    this.isStreaming = true;
                    this.startTime = Date.now();
                    this.frameCount = 0;
                } else {
                    console.log('⏸️ 화면 공유 중지됨');
                    this.updateStatus('⏸️ 대기 중', 'warning');
                    this.addLog('화면 공유가 중지되었습니다', 'warning');
                    this.isStreaming = false;
                    this.clearStream();
                }
                break;
                
            case 'video-frame':
                if (data.frame && this.isStreaming) {
                    this.displayVideoFrame(data.frame);
                }
                break;
                
            default:
                this.addLog(`알 수 없는 메시지 타입: ${data.type}`, 'warning');
        }
    }
    
    displayVideoFrame(frameData) {
        if (!this.streamBackground || !frameData) return;
        
        try {
            // 새 이미지 요소 생성
            const newImage = document.createElement('img');
            newImage.className = 'stream-image';
            newImage.src = frameData;
            
            newImage.onload = () => {
                try {
                    // 이전 이미지 제거
                    if (this.currentVideoElement && this.streamBackground.contains(this.currentVideoElement)) {
                        this.streamBackground.removeChild(this.currentVideoElement);
                    }
                    
                    // 새 이미지 추가
                    this.streamBackground.appendChild(newImage);
                    this.currentVideoElement = newImage;
                    
                    // 성능 통계 업데이트
                    this.frameCount++;
                    this.lastFrameTime = Date.now();
                    
                    // 첫 프레임 수신 시
                    if (this.isStreaming && this.frameCount === 1) {
                        this.hideLoadingIndicator();
                        this.updateStatus('📺 실시간 배경', 'success');
                        this.addLog('첫 프레임 수신됨', 'success');
                    }
                    
                    // 주기적으로 성능 통계 로그
                    if (this.frameCount % 100 === 0) {
                        const elapsed = (Date.now() - this.startTime) / 1000;
                        const fps = this.frameCount / elapsed;
                        this.addLog(`성능: ${this.frameCount}프레임, ${fps.toFixed(1)}fps`, 'info');
                    }
                    
                } catch (error) {
                    console.error('❌ 이미지 교체 오류:', error);
                    this.addLog(`이미지 교체 오류: ${error.message}`, 'error');
                }
            };
            
            newImage.onerror = () => {
                console.error('❌ 이미지 로드 실패');
                this.addLog('이미지 로드 실패', 'error');
                this.errorCount++;
            };
            
        } catch (error) {
            console.error('❌ 비디오 프레임 표시 오류:', error);
            this.addLog(`프레임 표시 오류: ${error.message}`, 'error');
            this.errorCount++;
        }
    }
    
    clearStream() {
        try {
            if (this.currentVideoElement && this.streamBackground && 
                this.streamBackground.contains(this.currentVideoElement)) {
                this.streamBackground.removeChild(this.currentVideoElement);
                this.currentVideoElement = null;
            }
            this.showLoadingIndicator();
            this.addLog('스트림 클리어됨', 'info');
        } catch (error) {
            console.error('❌ 스트림 클리어 오류:', error);
            this.addLog(`스트림 클리어 오류: ${error.message}`, 'error');
        }
    }
    
    hideLoadingIndicator() {
        if (this.loadingIndicator) {
            this.loadingIndicator.classList.add('hidden');
        }
    }
    
    showLoadingIndicator() {
        if (this.loadingIndicator) {
            this.loadingIndicator.classList.remove('hidden');
        }
    }
    
    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = Math.min(5000 * this.reconnectAttempts, 30000); // 최대 30초
        
        this.addLog(`${delay/1000}초 후 재연결 시도`, 'info');
        
        setTimeout(() => {
            this.connectToSignalingServer();
        }, delay);
    }
    
    manualReconnect() {
        console.log('🔄 F5 수동 재연결');
        this.addLog('수동 재연결 시작', 'info');
        this.reconnectAttempts = 0;
        this.updateStatus('🔄 재연결 중...', 'info');
        
        if (this.webrtcSocket) {
            this.webrtcSocket.close();
        }
        
        setTimeout(() => {
            this.connectToSignalingServer();
        }, 1000);
    }
    
    toggleStreaming() {
        const bg = this.streamBackground;
        if (bg) {
            if (bg.style.display === 'none') {
                bg.style.display = 'flex';
                this.updateStatus('📺 배경 표시', 'success');
                this.addLog('스트리밍 배경 표시', 'info');
            } else {
                bg.style.display = 'none';
                this.updateStatus('📺 배경 숨김', 'warning');
                this.addLog('스트리밍 배경 숨김', 'info');
            }
        }
    }
    
    getStats() {
        const elapsed = (Date.now() - this.startTime) / 1000;
        const fps = elapsed > 0 ? this.frameCount / elapsed : 0;
        
        return {
            frameCount: this.frameCount,
            fps: fps.toFixed(1),
            errorCount: this.errorCount,
            isStreaming: this.isStreaming,
            reconnectAttempts: this.reconnectAttempts,
            uptime: elapsed.toFixed(0)
        };
    }
    
    cleanup() {
        try {
            this.addLog('스트리밍 시스템 종료', 'info');
            if (this.webrtcSocket) {
                this.webrtcSocket.close();
            }
        } catch (error) {
            console.error('❌ 정리 오류:', error);
        }
    }
}

// 배경 스트리밍 인스턴스 생성
const backgroundStreaming = new BackgroundStreaming();

// 전역 함수로 통계 정보 제공
window.getStreamingStats = () => backgroundStreaming.getStats();

// 개발자 도구용 디버그 함수
window.debugStreaming = {
    getStats: () => backgroundStreaming.getStats(),
    reconnect: () => backgroundStreaming.manualReconnect(),
    toggle: () => backgroundStreaming.toggleStreaming(),
    clearStream: () => backgroundStreaming.clearStream()
};
// signaling_server.js - 새 2번 PC용 (172.18.73.63)
const WebSocket = require('ws');

console.log('🚀 WebRTC 시그널링 서버 초기화 중...');

class SignalingServer {
    constructor(port = 3001) {
        this.port = port;
        this.rooms = new Map();
        this.clients = new Map();
        this.frameCount = 0;
        this.lastFrameLog = 0;
        
        this.setupServer();
    }
    
    setupServer() {
        try {
            // WebSocket 서버 생성 (모든 IP에서 접근 가능)
            this.wss = new WebSocket.Server({ 
                port: this.port,
                host: '0.0.0.0'  // 모든 네트워크에서 접근 가능
            });
            
            this.wss.on('connection', (ws, req) => {
                this.handleConnection(ws, req);
            });
            
            this.wss.on('error', (error) => {
                console.error('❌ WebSocket 서버 오류:', error);
            });
            
            this.printStartupInfo();
            
        } catch (error) {
            console.error('❌ 서버 시작 실패:', error);
            process.exit(1);
        }
    }
    
    printStartupInfo() {
        console.log('='.repeat(70));
        console.log('🚀 WebRTC 시그널링 서버 시작됨 (같은 네트워크)');
        console.log('='.repeat(70));
        console.log(`📡 포트: ${this.port}`);
        console.log(`🌐 로컬 접속: ws://localhost:${this.port}`);
        console.log(`🌐 네트워크 접속: ws://172.18.73.63:${this.port}`);
        console.log(`🌐 모든 IP 허용: ws://0.0.0.0:${this.port}`);
        console.log('='.repeat(70));
        console.log('📋 연결 대기 중...');
        console.log('  - 1번 PC (172.18.73.60): 화면 송출 클라이언트');
        console.log('  - 2번 PC (172.18.73.63): Dash 뷰어');
        console.log('✅ 같은 네트워크 - 최적 연결 환경');
        console.log('='.repeat(70));
    }
    
    handleConnection(ws, req) {
        const clientId = this.generateId();
        const clientIP = req.socket.remoteAddress;
        console.log(`📱 클라이언트 연결: ${clientId} (IP: ${clientIP})`);
        
        // 클라이언트 정보 저장
        this.clients.set(clientId, {
            ws: ws,
            id: clientId,
            role: null,
            roomId: null,
            ip: clientIP
        });
        
        ws.on('message', (data) => {
            try {
                const message = JSON.parse(data.toString());
                this.handleMessage(clientId, message);
            } catch (error) {
                console.error('❌ 메시지 파싱 오류:', error);
            }
        });
        
        ws.on('close', () => {
            this.handleDisconnection(clientId);
        });
        
        ws.on('error', (error) => {
            console.error(`❌ 클라이언트 오류 (${clientId}):`, error);
        });
    }
    
    handleMessage(clientId, message) {
        const client = this.clients.get(clientId);
        if (!client) return;
        
        switch (message.type) {
            case 'join-room':
                this.handleJoinRoom(clientId, message);
                break;
                
            case 'screen-share-started':
                this.handleScreenShareStarted(clientId);
                break;
                
            case 'video-frame':
                this.handleVideoFrame(clientId, message);
                break;
                
            default:
                console.log(`🔍 알 수 없는 메시지 타입: ${message.type}`);
        }
    }
    
    handleJoinRoom(clientId, message) {
        const client = this.clients.get(clientId);
        const { roomId, role } = message;
        
        client.role = role;
        client.roomId = roomId;
        
        // 방이 없으면 생성
        if (!this.rooms.has(roomId)) {
            this.rooms.set(roomId, {
                streamer: null,
                viewers: new Set()
            });
        }
        
        const room = this.rooms.get(roomId);
        
        if (role === 'streamer') {
            room.streamer = clientId;
            console.log(`🎥 스트리머 입장: ${clientId} (IP: ${client.ip}) → 방: ${roomId}`);
            
            // 기존 뷰어들에게 스트리머 연결 알림
            room.viewers.forEach(viewerId => {
                const viewer = this.clients.get(viewerId);
                if (viewer && viewer.ws.readyState === WebSocket.OPEN) {
                    viewer.ws.send(JSON.stringify({
                        type: 'streamer-joined',
                        streamerId: clientId
                    }));
                }
            });
            
        } else if (role === 'viewer') {
            room.viewers.add(clientId);
            console.log(`📺 뷰어 입장: ${clientId} (IP: ${client.ip}) → 방: ${roomId}`);
            
            // 스트리머에게 새 뷰어 알림
            if (room.streamer) {
                const streamer = this.clients.get(room.streamer);
                if (streamer && streamer.ws.readyState === WebSocket.OPEN) {
                    streamer.ws.send(JSON.stringify({
                        type: 'viewer-joined',
                        viewerId: clientId,
                        viewerCount: room.viewers.size
                    }));
                }
            }
        }
        
        console.log(`📊 방 상태 [${roomId}] - 스트리머: ${room.streamer ? '연결됨' : '대기중'}, 뷰어: ${room.viewers.size}명`);
    }
    
    handleScreenShareStarted(clientId) {
        const client = this.clients.get(clientId);
        if (!client || !client.roomId) return;
        
        const room = this.rooms.get(client.roomId);
        if (!room) return;
        
        console.log(`🖥️ 화면 공유 시작: ${clientId} → ${room.viewers.size}명의 뷰어에게 전송`);
        
        // 모든 뷰어에게 화면 공유 시작 알림
        room.viewers.forEach(viewerId => {
            const viewer = this.clients.get(viewerId);
            if (viewer && viewer.ws.readyState === WebSocket.OPEN) {
                viewer.ws.send(JSON.stringify({
                    type: 'screen-share-status',
                    streaming: true,
                    streamerId: clientId
                }));
            }
        });
    }
    
    handleVideoFrame(clientId, message) {
        const client = this.clients.get(clientId);
        if (!client || !client.roomId) return;
        
        const room = this.rooms.get(client.roomId);
        if (!room) return;
        
        // 모든 뷰어에게 비디오 프레임 전송
        let sentCount = 0;
        room.viewers.forEach(viewerId => {
            const viewer = this.clients.get(viewerId);
            if (viewer && viewer.ws.readyState === WebSocket.OPEN) {
                try {
                    viewer.ws.send(JSON.stringify({
                        type: 'video-frame',
                        frame: message.frame,
                        timestamp: message.timestamp
                    }));
                    sentCount++;
                } catch (error) {
                    console.error(`❌ 프레임 전송 오류 (뷰어 ${viewerId}):`, error);
                }
            }
        });
        
        // 프레임 전송 통계 (5초마다 로그 - 더 자주)
        this.frameCount++;
        const now = Date.now();
        if (now - this.lastFrameLog > 5000) {
            console.log(`📊 프레임 통계: ${this.frameCount}프레임 전송됨 (뷰어 ${sentCount}명) - 같은 네트워크 고품질`);
            this.frameCount = 0;
            this.lastFrameLog = now;
        }
    }
    
    handleDisconnection(clientId) {
        const client = this.clients.get(clientId);
        if (!client) return;
        
        console.log(`📱 클라이언트 연결 해제: ${clientId} (IP: ${client.ip})`);
        
        // 방에서 제거
        if (client.roomId && this.rooms.has(client.roomId)) {
            const room = this.rooms.get(client.roomId);
            
            if (client.role === 'streamer' && room.streamer === clientId) {
                room.streamer = null;
                console.log(`🎥 스트리머 나감: ${clientId}`);
                
                // 모든 뷰어에게 스트리머 나감 알림
                room.viewers.forEach(viewerId => {
                    const viewer = this.clients.get(viewerId);
                    if (viewer && viewer.ws.readyState === WebSocket.OPEN) {
                        viewer.ws.send(JSON.stringify({
                            type: 'streamer-left'
                        }));
                    }
                });
                
            } else if (client.role === 'viewer') {
                room.viewers.delete(clientId);
                console.log(`📺 뷰어 나감: ${clientId}`);
                
                // 스트리머에게 뷰어 나감 알림
                if (room.streamer) {
                    const streamer = this.clients.get(room.streamer);
                    if (streamer && streamer.ws.readyState === WebSocket.OPEN) {
                        streamer.ws.send(JSON.stringify({
                            type: 'viewer-left',
                            viewerId: clientId,
                            viewerCount: room.viewers.size
                        }));
                    }
                }
            }
            
            // 빈 방 정리
            if (!room.streamer && room.viewers.size === 0) {
                this.rooms.delete(client.roomId);
                console.log(`🗑️ 빈 방 삭제: ${client.roomId}`);
            }
        }
        
        this.clients.delete(clientId);
        console.log(`📊 현재 연결: ${this.clients.size}개 클라이언트, ${this.rooms.size}개 방`);
    }
    
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    }
}

// 서버 시작
try {
    const server = new SignalingServer(3001);
    
    // 종료 처리
    process.on('SIGINT', () => {
        console.log('\n🛑 시그널링 서버 종료');
        process.exit(0);
    });
    
    // 오류 처리
    process.on('uncaughtException', (error) => {
        console.error('❌ 예상치 못한 오류:', error);
    });
    
    process.on('unhandledRejection', (reason, promise) => {
        console.error('❌ 처리되지 않은 Promise 거부:', reason);
    });
    
} catch (error) {
    console.error('❌ 서버 초기화 실패:', error);
    process.exit(1);
}
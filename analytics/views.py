from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import Avg, Count, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Conversation, ConversationAnalysis
from .serializers import (
    ConversationSerializer, ConversationCreateSerializer,
    ConversationAnalysisSerializer
)
from .services import ConversationAnalyzer

class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.prefetch_related('messages').all()
    serializer_class = ConversationSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        return ConversationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conv = serializer.save()
        out = ConversationSerializer(conv)
        return Response(out.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        conversation = self.get_object()
        if conversation.messages.count() == 0:
            return Response({'error':'Cannot analyze conversation with no messages'},
                             status=status.HTTP_400_BAD_REQUEST)
        try:
            analyzer = ConversationAnalyzer(conversation)
            analysis = analyzer.analyze()
            serializer = ConversationAnalysisSerializer(analysis)
            return Response({'message':'Analysis completed successfully','analysis':serializer.data})
        except Exception as e:
            return Response({'error':f'Analysis failed: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def bulk_analyze(self, request):
        pending = Conversation.objects.filter(Q(status='pending') | Q(analysis__isnull=True)).exclude(messages__isnull=True)
        results = {'success':[], 'failed':[]}
        for conv in pending:
            try:
                analyzer = ConversationAnalyzer(conv)
                analyzer.analyze()
                results['success'].append(conv.id)
            except Exception as e:
                results['failed'].append({'id':conv.id, 'error':str(e)})
        return Response({
            'total_processed': len(results['success']) + len(results['failed']),
            'successful': len(results['success']),
            'failed': len(results['failed']),
            'details': results
        })
    
    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        conversation = self.get_object()
        try:
            analysis = conversation.analysis
        except ConversationAnalysis.DoesNotExist:
            return Response({'error':'No analysis available. Please analyze first.'}, status=status.HTTP_404_NOT_FOUND)
        insights = {
            'total_messages': conversation.message_count,
            'user_messages': conversation.user_message_count,
            'ai_messages': conversation.ai_message_count,
            'conversation_quality': 'Excellent' if analysis.overall_score>=8 else
                                    'Good' if analysis.overall_score>=6 else
                                    'Fair' if analysis.overall_score>=4 else
                                    'Poor',
            'key_strengths': self._get_strengths(analysis),
            'areas_for_improvement': self._get_improvements(analysis),
        }
        data = {
            'conversation': ConversationSerializer(conversation).data,
            'analysis': ConversationAnalysisSerializer(analysis).data,
            'insights': insights
        }
        return Response(data)
    
    def _get_strengths(self, analysis):
        strengths = []
        if analysis.clarity_score >= 0.8:
            strengths.append('Clear communication')
        if analysis.empathy_score >= 0.7:
            strengths.append('Empathetic responses')
        if analysis.resolution:
            strengths.append('Issue resolved')
        if analysis.professionalism_score >= 0.8:
            strengths.append('Professional tone')
        return strengths or ['Basic functionality maintained']
    
    def _get_improvements(self, analysis):
        improvements = []
        if analysis.clarity_score < 0.6:
            improvements.append('Improve response clarity')
        if analysis.relevance_score < 0.6:
            improvements.append('Stay more focused on topic')
        if analysis.empathy_score < 0.5:
            improvements.append('Add more empathetic language')
        if analysis.fallback_count > 2:
            improvements.append('Reduce "I don\'t know" responses')
        if analysis.escalation_needed:
            improvements.append('Consider human handoff')
        return improvements or ['Continue maintaining quality']

def analytics_dashboard(request):
    total_conversations = Conversation.objects.count()
    analyzed = ConversationAnalysis.objects.count()
    pending = Conversation.objects.filter(status='pending').count()
    if analyzed > 0:
        avg_scores = ConversationAnalysis.objects.aggregate(
            avg_overall=Avg('overall_score'),
            avg_clarity=Avg('clarity_score'),
            avg_relevance=Avg('relevance_score'),
            avg_empathy=Avg('empathy_score')
        )
        sentiment_breakdown = {
            'positive': ConversationAnalysis.objects.filter(sentiment='positive').count(),
            'neutral': ConversationAnalysis.objects.filter(sentiment='neutral').count(),
            'negative': ConversationAnalysis.objects.filter(sentiment='negative').count(),
            'mixed': ConversationAnalysis.objects.filter(sentiment='mixed').count(),
        }
        escalation_rate = ConversationAnalysis.objects.filter(escalation_needed=True).count() / analyzed * 100
        resolution_rate = ConversationAnalysis.objects.filter(resolution=True).count() / analyzed * 100
    else:
        avg_scores = {
            'avg_overall': 0,
            'avg_clarity': 0,
            'avg_relevance': 0,
            'avg_empathy': 0,
        }
        sentiment_breakdown = {
            'positive': 0,
            'neutral': 0,
            'negative': 0,
            'mixed': 0,
        }
        escalation_rate = 0
        resolution_rate = 0
    
    context = {
        'overview': {
            'total_conversations': total_conversations,
            'analyzed': analyzed,
            'pending': pending,
        },
        'average_scores': avg_scores,
        'sentiment_breakdown': sentiment_breakdown,
        'metrics': {
            'resolution_rate': round(resolution_rate, 2),
            'escalation_rate': round(escalation_rate, 2),
        }
    }
    
    # Check if request wants JSON (API call)
    if request.META.get('HTTP_ACCEPT', '').find('application/json') != -1:
        return JsonResponse(context)
    
    return render(request, 'analytics/dashboard.html', context)

def trigger_analysis(request):
    if request.method == 'POST':
        conversation_id = request.POST.get('conversation_id')
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
                analyzer = ConversationAnalyzer(conversation)
                analysis = analyzer.analyze()
                messages.success(request, f'Analysis completed for conversation {conversation_id}')
                return redirect('trigger-analysis')
            except Conversation.DoesNotExist:
                messages.error(request, 'Conversation not found')
                return redirect('trigger-analysis')
            except Exception as e:
                messages.error(request, f'Analysis failed: {str(e)}')
                return redirect('trigger-analysis')
        else:
            # Trigger bulk analysis
            pending = Conversation.objects.filter(Q(status='pending') | Q(analysis__isnull=True)).exclude(messages__isnull=True)
            results = {'success':[], 'failed':[]}
            for conv in pending:
                try:
                    analyzer = ConversationAnalyzer(conv)
                    analyzer.analyze()
                    results['success'].append(conv.id)
                except Exception as e:
                    results['failed'].append({'id':conv.id, 'error':str(e)})
            
            total = len(results['success']) + len(results['failed'])
            successful = len(results['success'])
            failed = len(results['failed'])
            
            if successful > 0:
                messages.success(request, f'Successfully analyzed {successful} conversation(s)')
            if failed > 0:
                messages.warning(request, f'Failed to analyze {failed} conversation(s)')
            if total == 0:
                messages.info(request, 'No pending conversations to analyze')
            
            return redirect('trigger-analysis')
    else:
        # GET request - show the analyze page
        return render(request, 'analytics/analyze.html')


def home(request):
    return render(request, 'analytics/home.html')

